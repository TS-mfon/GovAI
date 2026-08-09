// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";

/// @title GovAIRegistry
/// @notice Permissionless registry of DAOs. Any address can register a DAO by
/// supplying its mission, constitution hash (IPFS CID), token (optional), and the
/// AI-gate thresholds the GenLayer decision contract will enforce.
contract GovAIRegistry is Ownable {
    uint256 public daoCount;

    struct DAOConfig {
        string name;
        string mission;
        bytes32 constitutionHash; // IPFS CID of the constitution text
        address token; // address(0) => no token, 1-address-1-vote
        uint256 chainId; // chain the token lives on (0 if no token)
        uint256 maxRisk; // 0-100, proposal rejected if risk exceeds
        uint256 minBenefit; // 0-100, proposal rejected if benefit below
        uint256 minConfidence; // 0-100, alignment confidence required
        uint256 votingDuration; // seconds the voting window stays open
        uint256 quorumBps; // 0-10000, % of total weight required to finalize
        bool delegationOn;
        address owner; // who registered / may update config
    }

    mapping(uint256 => DAOConfig) public daos;

    event DAORegistered(uint256 indexed daoId, address owner, string name);
    event DAOUpdated(uint256 indexed daoId, address owner);

    constructor() Ownable(msg.sender) {}

    function registerDAO(DAOConfig calldata cfg) external returns (uint256 daoId) {
        require(bytes(cfg.name).length > 0, "name required");
        daoId = ++daoCount;
        daos[daoId] = cfg;
        daos[daoId].owner = msg.sender;
        emit DAORegistered(daoId, msg.sender, cfg.name);
    }

    function updateConfig(uint256 daoId, DAOConfig calldata cfg) external {
        require(daos[daoId].owner == msg.sender, "not owner");
        daos[daoId] = cfg;
        daos[daoId].owner = msg.sender;
        emit DAOUpdated(daoId, msg.sender);
    }

    function getDAO(uint256 daoId) external view returns (DAOConfig memory) {
        return daos[daoId];
    }
}
