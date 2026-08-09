// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/// @title Delegation
/// @notice Per-DAO vote delegation (single-level for MVP; liquid/multi-level is an
/// enhancement). A delegator routes their voting weight to a delegate, who can then
/// cast a vote that also counts the delegator's weight.
contract Delegation {
    address public governor; // ProposalRegistry

    // daoId => delegator => delegate
    mapping(uint256 => mapping(address => address)) public delegation;

    event Delegated(uint256 indexed daoId, address indexed delegator, address indexed delegate);

    error NotGovernor();

    function setGovernor(address g) external {
        if (governor != address(0)) revert NotGovernor();
        governor = g;
    }

    function delegate(uint256 daoId, address to) external {
        require(to != msg.sender, "cannot delegate to self");
        require(to != address(0), "zero delegate");
        delegation[daoId][msg.sender] = to;
        emit Delegated(daoId, msg.sender, to);
    }

    function undelegate(uint256 daoId) external {
        delegation[daoId][msg.sender] = address(0);
        emit Delegated(daoId, msg.sender, address(0));
    }

    function getDelegation(uint256 daoId, address who) external view returns (address) {
        return delegation[daoId][who];
    }
}
