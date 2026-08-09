import { getContractAddress } from "./env";

// ---- ABIs (subset used by the frontend) ----

export const votingAbi = [
  {
    type: "function",
    name: "castVote",
    stateMutability: "nonpayable",
    inputs: [
      { name: "proposalId", type: "uint256" },
      { name: "daoId", type: "uint256" },
      { name: "token", type: "address" },
      { name: "chainId", type: "uint256" },
      { name: "support", type: "bool" },
      { name: "claimedWeight", type: "uint256" },
      { name: "proof", type: "bytes32[]" },
      { name: "delegators", type: "address[]" },
      { name: "delegatorWeights", type: "uint256[]" },
      { name: "delegatorProofs", type: "bytes32[][]" },
    ],
    outputs: [],
  },
] as const;

export const delegationAbi = [
  {
    type: "function",
    name: "delegate",
    stateMutability: "nonpayable",
    inputs: [
      { name: "daoId", type: "uint256" },
      { name: "to", type: "address" },
    ],
    outputs: [],
  },
] as const;

export const VOTING_ADDR = getContractAddress("NEXT_PUBLIC_VOTING_ADDR");
export const DELEGATION_ADDR = getContractAddress("NEXT_PUBLIC_DELEGATION_ADDR");
