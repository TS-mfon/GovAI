// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/// @notice Interface the GovAI relayer (backend watching GenLayer) calls to deliver
/// the AI decision (alignment + scores + threshold verdict) produced by the GenLayer
/// Intelligent Contract. Implemented by ProposalRegistry.
interface IGovAIDecision {
    struct AIReport {
        bool passed; // false => proposal rejected by the AI gate
        string reason; // human-readable rejection reason (or "passed AI gate")
        uint8 intentClarity; // 0-100
        uint8 benefitScore; // 0-100
        uint8 riskScore; // 0-100
        bool selfDealing; // self-dealing flag raised by GenLayer
        bool malicious; // malicious flag raised by GenLayer
        uint8 confidence; // 0-100 (alignment confidence)
    }

    /// @dev Only the authorised relayer may call this.
    function submitAIReport(uint256 proposalId, AIReport calldata report) external;
}
