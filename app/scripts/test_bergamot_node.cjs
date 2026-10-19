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

async function main() {
  const wasmPath = path.join(__dirname, '..', 'data', 'bergamot', 'bergamot-translator-worker.wasm');
  const gluePath = path.join(__dirname, '..', 'data', 'bergamot', 'bergamot-translator-worker.js');

  const binary = fs.readFileSync(wasmPath);
  console.log("Read binary bytes:", binary.length);

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

  const Module = {
    instantiateWasm(imports, accept) {
      console.log("instantiateWasm called!");
      WebAssembly.instantiate(binary, { ...imports, wasm_gemm: gemmImports(Module) })
        .then((result) => {
          console.log("WebAssembly instantiated successfully!");
          accept(result.instance);
        })
        .catch((err) => {
          console.error("Wasm instantiation error:", err);
        });
      return {};
    },
    onRuntimeInitialized() {
      console.log("Bergamot runtime initialized successfully via VM in Node.js!");
      const types = Object.keys(Module).filter(k => k.includes('Translation') || k.includes('Service') || k.includes('Vector') || k.includes('Aligned'));
      console.log("Exported types on Module:", types);
      process.exit(0);
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
}

main().catch(console.error);
