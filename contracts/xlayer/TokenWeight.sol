// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/utils/cryptography/MerkleProof.sol";

/// @title TokenWeight
/// @notice Resolves a voter's voting weight for a proposal.
/// Two modes (chosen per DAO at proposal time):
///   MODE A (native): DAO token lives on X Layer -> read ERC20.balanceOf(voter) directly.
///   MODE B (external): DAO token lives on another EVM chain -> the GovAI backend
///           verified balances via the Etherscan-compatible explorer API at a snapshot
///           block, built a Merkle tree (voter -> weight), and stored the root here.
///           Voters supply a Merkle proof; their claimed weight is returned if valid.
contract TokenWeight {
    address public governor; // ProposalRegistry, the only caller allowed
    uint256 public immutable xlayerChainId;

    // proposalId => merkle root for MODE B
    mapping(uint256 => bytes32) public roots;

    event SnapshotRootSet(uint256 indexed proposalId, bytes32 root);

    error NotGovernor();
    error NoRoot();

    constructor(uint256 _xlayerChainId) {
        xlayerChainId = _xlayerChainId;
    }

    function setGovernor(address g) external {
        if (governor != address(0)) revert NotGovernor();
        governor = g;
    }

    /// @notice Relayer sets the Merkle root for an external-token proposal.
    function setSnapshotRoot(uint256 proposalId, bytes32 root) external {
        if (msg.sender != governor) revert NotGovernor();
        roots[proposalId] = root;
        emit SnapshotRootSet(proposalId, root);
    }

    /// @notice Voting weight of `voter` for `proposalId`.
    /// @param token DAO token address (address(0) => 1-address-1-vote, weight = 1).
    /// @param chainId chain the token lives on.
    /// @param claimedWeight voter's claimed weight (used only in MODE B for the leaf).
    /// @param proof Merkle proof (MODE B); empty in MODE A.
    function weightOf(
        address token,
        uint256 chainId,
        uint256 proposalId,
        address voter,
        uint256 claimedWeight,
        bytes32[] calldata proof
    ) external view returns (uint256) {
        // No token => 1 address = 1 vote.
        if (token == address(0)) return 1;

        // MODE A: native X Layer token.
        if (chainId == xlayerChainId) {
            return IERC20(token).balanceOf(voter);
        }

        // MODE B: external token verified off-chain via Etherscan, proven on-chain.
        bytes32 root = roots[proposalId];
        if (root == bytes32(0)) revert NoRoot();
        bytes32 leaf = keccak256(abi.encodePacked(voter, claimedWeight));
        if (MerkleProof.verify(proof, root, leaf)) return claimedWeight;
        return 0;
    }
}
