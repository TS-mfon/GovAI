// Deploys GovAI's X Layer contracts in dependency order and writes addresses to deployed.json.
// Run:  XLAYER_RPC=... DEPLOYER_PK=0x... XLAYER_CHAIN_ID=195 RELAYER_ADDR=0x... npx hardhat run 00_deploy_xlayer.js --network xlayerTestnet
const hre = require("hardhat");
const fs = require("fs");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  const xlayerChainId = Number(process.env.XLAYER_CHAIN_ID || 195);
  const relayer = process.env.RELAYER_ADDR || deployer.address;

  const TokenWeight = await hre.ethers.getContractFactory("TokenWeight");
  const tw = await TokenWeight.deploy(xlayerChainId);
  await tw.waitForDeployment();

  const Delegation = await hre.ethers.getContractFactory("Delegation");
  const del = await Delegation.deploy();
  await del.waitForDeployment();

  const Voting = await hre.ethers.getContractFactory("Voting");
  const voting = await Voting.deploy();
  await voting.waitForDeployment();

  const Registry = await hre.ethers.getContractFactory("GovAIRegistry");
  const reg = await Registry.deploy();
  await reg.waitForDeployment();

  const ProposalRegistry = await hre.ethers.getContractFactory("ProposalRegistry");
  const prop = await ProposalRegistry.deploy(
    await reg.getAddress(),
    await voting.getAddress(),
    await tw.getAddress(),
    await del.getAddress(),
    relayer,
    xlayerChainId
  );
  await prop.waitForDeployment();

  const out = {
    registry: await reg.getAddress(),
    tokenWeight: await tw.getAddress(),
    delegation: await del.getAddress(),
    voting: await voting.getAddress(),
    proposalRegistry: await prop.getAddress(),
  };
  console.log(JSON.stringify(out, null, 2));
  fs.writeFileSync("deployed.json", JSON.stringify(out, null, 2));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
