const fs = require('fs');
const path = require('path');
const vm = require('vm');

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

async function main() {
  const wasmPath = path.join(__dirname, '..', 'data', 'bergamot', 'bergamot-translator-worker.wasm');
  const gluePath = path.join(__dirname, '..', 'data', 'bergamot', 'bergamot-translator-worker.js');

  const binary = fs.readFileSync(wasmPath);

  const sandbox = {
    console,
    WebAssembly,
    setTimeout,
    clearTimeout,
    setInterval,
    clearInterval,
    TextDecoder,
    TextEncoder,
  };

  let Module;

  await new Promise((resolve) => {
    Module = {
      instantiateWasm(imports, accept) {
        WebAssembly.instantiate(binary, { ...imports, wasm_gemm: gemmImports(Module) })
          .then((result) => accept(result.instance))
          .catch(console.error);
        return {};
      },
      onRuntimeInitialized() {
        resolve();
      },
      print: (msg) => console.log("[bergamot]", msg),
      printErr: (msg) => console.warn("[bergamot err]", msg),
    };

    sandbox.Module = Module;
    sandbox.global = sandbox;
    sandbox.self = sandbox;
    sandbox.globalThis = sandbox;

    const glueCode = fs.readFileSync(gluePath, 'utf8');
    vm.createContext(sandbox);
    vm.runInContext(glueCode, sandbox);
  });

  console.log("Loading envi model files...");
  const modelDir = path.join(__dirname, '..', 'data', 'models', 'envi');
  const modelBuf = fs.readFileSync(path.join(modelDir, 'model.envi.intgemm.alphas.bin'));
  const shortlistBuf = fs.readFileSync(path.join(modelDir, 'lex.50.50.envi.s2t.bin'));
  const vocabBuf = fs.readFileSync(path.join(modelDir, 'vocab.envi.spm'));

  const vocabs = new Module.AlignedMemoryList();
  // vocab is source and target
  vocabs.push_back(alignedCopy(Module, vocabBuf.buffer.slice(vocabBuf.byteOffset, vocabBuf.byteOffset + vocabBuf.byteLength), 64));

  console.log("Constructing TranslationModel...");
  const model = new Module.TranslationModel(
    modelConfigYaml(),
    alignedCopy(Module, modelBuf.buffer.slice(modelBuf.byteOffset, modelBuf.byteOffset + modelBuf.byteLength), 256),
    alignedCopy(Module, shortlistBuf.buffer.slice(shortlistBuf.byteOffset, shortlistBuf.byteOffset + shortlistBuf.byteLength), 64),
    vocabs,
    null
  );

  console.log("Constructing BlockingService...");
  const service = new Module.BlockingService({ cacheSize: 0 });

  const testSentences = [
    "Hello world! This is offline translation.",
    "Learning a new language is wonderful.",
    "Highlight text on desktop to translate instantly."
  ];

  console.log("Translating sentences:", testSentences);
  const input = new Module.VectorString();
  const options = new Module.VectorResponseOptions();

  for (const text of testSentences) {
    input.push_back(text);
    options.push_back({ alignment: false, html: false, qualityScores: false });
  }

  const startTime = Date.now();
  const responses = service.translate(model, input, options);
  const duration = Date.now() - startTime;

  console.log(`\n=== Translation Results (Took ${duration} ms) ===`);
  for (let i = 0; i < testSentences.length; i++) {
    console.log(`EN: ${testSentences[i]}`);
    console.log(`VI: ${responses.get(i).getTranslatedText()}\n`);
  }

  input.delete();
  options.delete();
  responses.delete();
}

main().catch(console.error);
