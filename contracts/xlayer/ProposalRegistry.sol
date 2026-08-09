// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";
import "./GovAIRegistry.sol";
import "./Voting.sol";
import "./TokenWeight.sol";
import "./Delegation.sol";
import "./interfaces/IGovAIDecision.sol";

/// @title ProposalRegistry
/// @notice The on-chain source of truth for GovAI proposals on X Layer.
/// Lifecycle: Submitted -> (AIReview) -> Voting | Rejected -> Executed | Defeated.
/// The AI decision arrives from the GenLayer Intelligent Contract via the relayer
/// (backend) calling submitAIReport (IGovAIDecision). External-token weights are
/// snapshotted by the relayer (Etherscan-verified Merkle root) before voting opens.
contract ProposalRegistry is IGovAIDecision, Ownable {
    GovAIRegistry public registry;
    Voting public voting;
    TokenWeight public tokenWeight;
    address public relayer;

    enum Stage { Submitted, AIReview, Voting, Executed, Defeated, Rejected }

    struct Proposal {
        uint256 daoId;
        address proposer;
        bytes32 proposalCid;
        bytes32 constitutionCid;
        Stage stage;
        uint256 createdAt;
        uint256 votingEndsAt;
        uint256 totalWeight; // for quorum; set by relayer (both modes)
        uint256 quorumBps;
        AIReport report;
    }

    mapping(uint256 => Proposal) public proposals;
    uint256 public proposalCount;

    event ProposalSubmitted(uint256 indexed proposalId, uint256 indexed daoId, address proposer);
    event AIReportSubmitted(uint256 indexed proposalId, bool passed);
    event SnapshotSet(uint256 indexed proposalId, uint256 totalWeight);
    event Finalized(uint256 indexed proposalId, Stage stage);

    error NotRelayer();
    error BadStage();
    error VotingOpen();

    constructor(
        address _registry,
        address _voting,
        address _tokenWeight,
        address _delegation,
        address _relayer,
        uint256 _xlayerChainId
    ) Ownable(msg.sender) {
        registry = GovAIRegistry(_registry);
        voting = Voting(_voting);
        tokenWeight = TokenWeight(_tokenWeight);
        relayer = _relayer;

        TokenWeight(_tokenWeight).setGovernor(address(this));
        Voting(_voting).setGovernor(address(this));
        Voting(_voting).setDependencies(TokenWeight(_tokenWeight), Delegation(_delegation));
    }

    function setRelayer(address r) external onlyOwner {
        relayer = r;
    }

    /// @notice DAO member submits a proposal. Text/actions live on IPFS (CIDs).
    function submitProposal(
        uint256 daoId,
        bytes32 proposalCid,
        bytes32 constitutionCid
    ) external returns (uint256 proposalId) {
        proposalId = ++proposalCount;
        Proposal storage p = proposals[proposalId];
        p.daoId = daoId;
        p.proposer = msg.sender;
        p.proposalCid = proposalCid;
        p.constitutionCid = constitutionCid;
        p.stage = Stage.Submitted;
        p.createdAt = block.timestamp;
        emit ProposalSubmitted(proposalId, daoId, msg.sender);
    }

    /// @notice Relayer delivers the GenLayer AI decision. Opens voting if passed.
    function submitAIReport(uint256 proposalId, AIReport calldata report) external {
        if (msg.sender != relayer) revert NotRelayer();
        Proposal storage p = proposals[proposalId];
        if (p.stage != Stage.Submitted && p.stage != Stage.Rejected) revert BadStage();
        p.report = report;
        if (report.passed) {
            GovAIRegistry.DAOConfig memory cfg = registry.getDAO(p.daoId);
            p.stage = Stage.Voting;
            p.votingEndsAt = block.timestamp + cfg.votingDuration;
            p.quorumBps = cfg.quorumBps;
            emit AIReportSubmitted(proposalId, true);
        } else {
            p.stage = Stage.Rejected;
            emit AIReportSubmitted(proposalId, false);
        }
    }

    /// @notice Relayer sets the (external-token) Merkle root and total weight so
    /// voting can be weighted and quorum computed. Call after submitAIReport(passed).
    function setVotingSnapshot(uint256 proposalId, bytes32 root, uint256 totalWeight) external {
        if (msg.sender != relayer) revert NotRelayer();
        Proposal storage p = proposals[proposalId];
        if (p.stage != Stage.Voting) revert BadStage();
        if (root != bytes32(0)) tokenWeight.setSnapshotRoot(proposalId, root);
        p.totalWeight = totalWeight;
        emit SnapshotSet(proposalId, totalWeight);
    }

    /// @notice Finalize after the voting window. Quorum + simple majority => Executed.
    function finalize(uint256 proposalId) external {
        Proposal storage p = proposals[proposalId];
        if (p.stage != Stage.Voting) revert BadStage();
        if (block.timestamp < p.votingEndsAt) revert VotingOpen();
        (uint256 forV, uint256 againstV, ) = voting.getTally(proposalId);
        uint256 quorum = (p.totalWeight * p.quorumBps) / 10000;
        if (forV + againstV >= quorum && forV > againstV) p.stage = Stage.Executed;
        else p.stage = Stage.Defeated;
        emit Finalized(proposalId, p.stage);
    }

    function getProposal(uint256 proposalId) external view returns (Proposal memory) {
        return proposals[proposalId];
    }
}
