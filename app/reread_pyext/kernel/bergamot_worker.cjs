/**
 * Bergamot Translation Worker running in Node.js.
 * Communicates with the Python Translation Kernel via JSON over stdin/stdout.
 */

const fs = require('fs');
const path = require('path');
const vm = require('vm');
const readline = require('readline');

const GEMM_FALLBACKS = {
  int8_prepare_a: "int8PrepareAFallback",
  int8_prepare_b: "int8PrepareBFallback",
  int8_prepare_b_from_transposed: "int8PrepareBFromTransposedFallback",
  int8_prepare_b_from_quantized_transposed: "int8PrepareBFromQuantizedTransposedFallback",
  int8_prepare_bias: "int8PrepareBiasFallback",
  int8_multiply_and_add_bias: "int8MultiplyAndAddBiasFallback",
  int8_select_columns_of_b: "int8SelectColumnsOfBFallback",
};

function gemmImports(Module) {
  return Object.fromEntries(
    Object.entries(GEMM_FALLBACKS).map(([imported, exported]) => [
      imported,
      (...args) => Module.asm[exported]?.(...args),
    ])
  );
}

function modelConfigYaml() {
  return [
    "beam-size: 1",
    "normalize: 1.0",
    "word-penalty: 0",
    "cpu-threads: 0",
    "gemm-precision: int8shiftAlphaAll",
    "skip-cost: true",
    "alignment: soft",
    "quiet: true",
    "quiet-translation: true",
    "max-length-break: 128",
    "mini-batch-words: 1024",
    "workspace: 128",
    "max-length-factor: 2.0",
  ].join("\n") + "\n";
}

function alignedCopy(module, buffer, alignment) {
  const bytes = new Int8Array(buffer);
  const memory = new module.AlignedMemory(bytes.byteLength, alignment);
  memory.getByteArrayView().set(bytes);
  return memory;
}

let Module = null;
let service = null;
const loadedModels = new Map();

async function initEngine(baseDir) {
  const wasmPath = path.join(baseDir, 'data', 'bergamot', 'bergamot-translator-worker.wasm');
  const gluePath = path.join(baseDir, 'data', 'bergamot', 'bergamot-translator-worker.js');

  const binary = fs.readFileSync(wasmPath);
  const sandbox = { console, WebAssembly, setTimeout, clearTimeout, setInterval, clearInterval, TextDecoder, TextEncoder };

  await new Promise((resolve) => {
    Module = {
      instantiateWasm(imports, accept) {
        WebAssembly.instantiate(binary, { ...imports, wasm_gemm: gemmImports(Module) })
          .then((result) => accept(result.instance))
          .catch((e) => {
            sendResponse({ type: 'error', message: 'Wasm instantiation failed: ' + e.message });
          });
        return {};
      },
      onRuntimeInitialized: resolve,
      print: () => {},
      printErr: () => {},
    };
    sandbox.Module = Module;
    sandbox.global = sandbox;
    sandbox.self = sandbox;
    sandbox.globalThis = sandbox;
    vm.createContext(sandbox);
    vm.runInContext(fs.readFileSync(gluePath, 'utf8'), sandbox);
  });

  service = new Module.BlockingService({ cacheSize: 0 });
}

function getOrLoadModel(modelsDir, pair) {
  if (loadedModels.has(pair)) {
    return loadedModels.get(pair);
  }

  const modelDir = path.join(modelsDir, pair);
  const modelFile = path.join(modelDir, `model.${pair}.intgemm.alphas.bin`);
  const shortlistFile = path.join(modelDir, `lex.50.50.${pair}.s2t.bin`);
  const vocabFile = path.join(modelDir, `vocab.${pair}.spm`);

  if (!fs.existsSync(modelFile) || !fs.existsSync(shortlistFile) || !fs.existsSync(vocabFile)) {
    throw new Error(`Model files for pair '${pair}' not found on disk.`);
  }

  const modelBuf = fs.readFileSync(modelFile);
  const shortlistBuf = fs.readFileSync(shortlistFile);
  const vocabBuf = fs.readFileSync(vocabFile);

  const vocabs = new Module.AlignedMemoryList();
  vocabs.push_back(alignedCopy(Module, vocabBuf.buffer.slice(vocabBuf.byteOffset, vocabBuf.byteOffset + vocabBuf.byteLength), 64));

  const model = new Module.TranslationModel(
    modelConfigYaml(),
    alignedCopy(Module, modelBuf.buffer.slice(modelBuf.byteOffset, modelBuf.byteOffset + modelBuf.byteLength), 256),
    alignedCopy(Module, shortlistBuf.buffer.slice(shortlistBuf.byteOffset, shortlistBuf.byteOffset + shortlistBuf.byteLength), 64),
    vocabs,
    null
  );

  loadedModels.set(pair, model);
  return model;
}

function translateSingle(modelsDir, pair, texts) {
  const model = getOrLoadModel(modelsDir, pair);
  const input = new Module.VectorString();
  const options = new Module.VectorResponseOptions();

  for (const text of texts) {
    input.push_back(text);
    options.push_back({ alignment: false, html: false, qualityScores: false });
  }

  const responses = service.translate(model, input, options);
  const results = texts.map((_, i) => responses.get(i).getTranslatedText());

  input.delete();
  options.delete();
  responses.delete();
  return results;
}

function sendResponse(obj) {
  process.stdout.write(JSON.stringify(obj) + '\n');
}

async function main() {
  const assetRoot = path.resolve(__dirname, '..', '..');
  const modelsDir = process.env.REREAD_MODELS_DIR
    ? path.resolve(process.env.REREAD_MODELS_DIR)
    : path.join(assetRoot, 'data', 'models');
  await initEngine(assetRoot);
  sendResponse({ type: 'ready' });

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false,
  });

  rl.on('line', (line) => {
    if (!line.trim()) return;
    let requestId;
    try {
      const req = JSON.parse(line);
      const { id, action, pair, texts, pipeline } = req;
      requestId = id;

      if (action === 'translate') {
        let currentTexts = texts;
        const startTime = Date.now();

        if (pipeline && Array.isArray(pipeline)) {
          for (const stepPair of pipeline) {
          currentTexts = translateSingle(modelsDir, stepPair, currentTexts);
          }
        } else if (pair) {
          currentTexts = translateSingle(modelsDir, pair, currentTexts);
        } else {
          throw new Error('Either pair or pipeline must be specified');
        }

        const duration = Date.now() - startTime;
        sendResponse({ id, type: 'result', results: currentTexts, durationMs: duration });
      } else if (action === 'preload') {
        getOrLoadModel(modelsDir, pair);
        sendResponse({ id, type: 'preloaded', pair });
      } else if (action === 'ping') {
        sendResponse({ id, type: 'pong' });
      }
    } catch (err) {
      sendResponse({ id: requestId, type: 'error', message: err.message });
    }
  });
}

main().catch((err) => {
  sendResponse({ type: 'error', message: err.message });
  process.exit(1);
});
