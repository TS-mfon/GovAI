// Hardhat config for deploying GovAI's X Layer (OKX L2) governance contracts.
// `contracts/` is a junction -> ../contracts so hardhat treats xlayer/*.sol as local.
require("@nomicfoundation/hardhat-toolbox");

/** @type {import('hardhat/config').HardhatUserConfig} */
module.exports = {
  solidity: {
    compilers: [
      {
        version: "0.8.20",
        settings: { viaIR: true, optimizer: { enabled: true, runs: 200 } },
      },
      {
        version: "0.8.19",
        settings: { viaIR: true, optimizer: { enabled: true, runs: 200 } },
      },
    ],
  },
  paths: {
    sources: "./contracts/xlayer",
    tests: "./tests",
    cache: "./cache",
    artifacts: "./artifacts",
  },
  networks: {
    xlayerTestnet: {
      url: process.env.XLAYER_RPC || "https://testrpc.xlayer.tech",
      accounts: process.env.DEPLOYER_PK ? [process.env.DEPLOYER_PK] : [],
      chainId: Number(process.env.XLAYER_CHAIN_ID || 195),
    },
    localhost: {
      url: "http://127.0.0.1:8545",
    },
  },
};
