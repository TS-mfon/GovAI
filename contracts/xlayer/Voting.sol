// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "./TokenWeight.sol";
import "./Delegation.sol";

/// @title Voting
/// @notice Token-weighted voting for GovAI proposals. Supports both native (X Layer)
/// and external (Merkle-proven) token weights via TokenWeight, plus single-level
/// delegation: a delegate may cast one vote that also carries their direct delegators'
/// weights.
contract Voting {
    address public governor; // ProposalRegistry
    TokenWeight public tokenWeight;
    Delegation public delegation;

    struct Tally {
        uint256 forVotes;
        uint256 againstVotes;
        uint256 voters;
    }

    mapping(uint256 => Tally) public tallies;
    mapping(uint256 => mapping(address => bool)) public hasVoted;

    event Voted(uint256 indexed proposalId, address indexed voter, bool support, uint256 weight);

    error NotGovernor();
    error AlreadyVoted();
    error NoWeight();
    error LenMismatch();

    function setGovernor(address g) external {
        if (governor != address(0)) revert NotGovernor();
        governor = g;
    }

    function setDependencies(TokenWeight tw, Delegation del) external {
        if (msg.sender != governor) revert NotGovernor();
        tokenWeight = tw;
        delegation = del;
    }

    /// @param daoId used for delegation lookup.
    /// @param token/chainId identify the DAO's token (passed from ProposalRegistry).
    /// @param claimedWeight/proof: self weight proof (MODE B). MODE A ignores them.
    /// @param delegators/delegatorWeights/delegatorProofs: direct delegators the caller
    ///        represents. Empty arrays for a plain self-vote.
    function castVote(
        uint256 proposalId,
        uint256 daoId,
        address token,
        uint256 chainId,
        bool support,
        uint256 claimedWeight,
        bytes32[] calldata proof,
        address[] calldata delegators,
        uint256[] calldata delegatorWeights,
        bytes32[][] calldata delegatorProofs
    ) external {
        if (hasVoted[proposalId][msg.sender]) revert AlreadyVoted();

        uint256 w = tokenWeight.weightOf(token, chainId, proposalId, msg.sender, claimedWeight, proof);
        _record(proposalId, msg.sender, support, w);

        if (delegators.length != delegatorWeights.length || delegators.length != delegatorProofs.length)
            revert LenMismatch();

        for (uint256 i = 0; i < delegators.length; i++) {
            address d = delegators[i];
            if (d == msg.sender) continue;
            if (delegation.getDelegation(daoId, d) != msg.sender) continue; // must delegate to caller
            if (hasVoted[proposalId][d]) continue;
            uint256 dw = tokenWeight.weightOf(token, chainId, proposalId, d, delegatorWeights[i], delegatorProofs[i]);
            _record(proposalId, d, support, dw);
        }
    }

    function _record(uint256 proposalId, address voter, bool support, uint256 w) internal {
        if (w == 0) revert NoWeight();
        hasVoted[proposalId][voter] = true;
        Tally storage t = tallies[proposalId];
        if (support) t.forVotes += w;
        else t.againstVotes += w;
        t.voters += 1;
        emit Voted(proposalId, voter, support, w);
    }

    function getTally(uint256 proposalId)
        external
        view
        returns (uint256 forVotes, uint256 againstVotes, uint256 voters)
    {
        Tally storage t = tallies[proposalId];
        return (t.forVotes, t.againstVotes, t.voters);
    }
}
