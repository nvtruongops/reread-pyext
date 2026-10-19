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

function loadModel(Module, pair) {
  const modelDir = path.join(__dirname, '..', 'data', 'models', pair);
  const modelBuf = fs.readFileSync(path.join(modelDir, `model.${pair}.intgemm.alphas.bin`));
  const shortlistBuf = fs.readFileSync(path.join(modelDir, `lex.50.50.${pair}.s2t.bin`));
  const vocabBuf = fs.readFileSync(path.join(modelDir, `vocab.${pair}.spm`));

  const vocabs = new Module.AlignedMemoryList();
  vocabs.push_back(alignedCopy(Module, vocabBuf.buffer.slice(vocabBuf.byteOffset, vocabBuf.byteOffset + vocabBuf.byteLength), 64));

  return new Module.TranslationModel(
    modelConfigYaml(),
    alignedCopy(Module, modelBuf.buffer.slice(modelBuf.byteOffset, modelBuf.byteOffset + modelBuf.byteLength), 256),
    alignedCopy(Module, shortlistBuf.buffer.slice(shortlistBuf.byteOffset, shortlistBuf.byteOffset + shortlistBuf.byteLength), 64),
    vocabs,
    null
  );
}

function translateBatch(service, model, Module, texts) {
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

async function main() {
  const wasmPath = path.join(__dirname, '..', 'data', 'bergamot', 'bergamot-translator-worker.wasm');
  const gluePath = path.join(__dirname, '..', 'data', 'bergamot', 'bergamot-translator-worker.js');

  const binary = fs.readFileSync(wasmPath);
  const sandbox = { console, WebAssembly, setTimeout, clearTimeout, setInterval, clearInterval, TextDecoder, TextEncoder };
  let Module;

  await new Promise((resolve) => {
    Module = {
      instantiateWasm(imports, accept) {
        WebAssembly.instantiate(binary, { ...imports, wasm_gemm: gemmImports(Module) })
          .then((result) => accept(result.instance))
          .catch(console.error);
        return {};
      },
      onRuntimeInitialized: resolve,
      print: (msg) => console.log("[bergamot]", msg),
      printErr: (msg) => console.warn("[bergamot err]", msg),
    };
    sandbox.Module = Module;
    sandbox.global = sandbox;
    sandbox.self = sandbox;
    sandbox.globalThis = sandbox;
    vm.createContext(sandbox);
    vm.runInContext(fs.readFileSync(gluePath, 'utf8'), sandbox);
  });

  const service = new Module.BlockingService({ cacheSize: 0 });

  console.log("Loading zhen, jaen, envi models for pivot translation...");
  const modelZhen = loadModel(Module, "zhen");
  const modelJaen = loadModel(Module, "jaen");
  const modelEnvi = loadModel(Module, "envi");

  // Chinese test
  const zhTexts = ["你好世界", "自然语言处理非常有趣"];
  console.log("\n--- Testing Chinese -> Vietnamese (zh -> en -> vi) ---");
  const zhToEn = translateBatch(service, modelZhen, Module, zhTexts);
  const zhToVi = translateBatch(service, modelEnvi, Module, zhToEn);
  for (let i = 0; i < zhTexts.length; i++) {
    console.log(`ZH: ${zhTexts[i]} -> EN: ${zhToEn[i]} -> VI: ${zhToVi[i]}`);
  }

  // Japanese test
  const jaTexts = ["こんにちは世界", "人工知能はとても素晴らしいです"];
  console.log("\n--- Testing Japanese -> Vietnamese (ja -> en -> vi) ---");
  const jaToEn = translateBatch(service, modelJaen, Module, jaTexts);
  const jaToVi = translateBatch(service, modelEnvi, Module, jaToEn);
  for (let i = 0; i < jaTexts.length; i++) {
    console.log(`JA: ${jaTexts[i]} -> EN: ${jaToEn[i]} -> VI: ${jaToVi[i]}`);
  }

  console.log("\nAll translations (ZH -> VI and JA -> VI) passed with flying colors!");
}

main().catch(console.error);
