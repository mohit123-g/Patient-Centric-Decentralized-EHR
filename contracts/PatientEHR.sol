// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract PatientEHR {
    address public owner;

    struct Record {
        string recordId;
        string patientId;
        string doctorId;
        string title;
        bytes32 recordHash;
        uint256 createdAt;
        bool exists;
    }

    struct Permission {
        uint256 validUntil;
        bool granted;
    }

    // IMPORTANT: permissions is a flat bytes32 mapping.
    // This matches the _permissionKey() function and avoids
    // the nested-mapping assignment error.
    mapping(bytes32 => Record) private records;
    mapping(bytes32 => Permission) private permissions;
    bytes32[] private recordKeys;

    event RecordCreated(
        string recordId,
        string patientId,
        string doctorId,
        bytes32 recordHash,
        uint256 createdAt
    );

    event AccessGranted(
        string recordId,
        string patientId,
        string doctorId,
        uint256 validUntil
    );

    event AccessRevoked(
        string recordId,
        string patientId,
        string doctorId
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can perform this action");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function _recordKey(string memory recordId) internal pure returns (bytes32) {
        return keccak256(abi.encodePacked(recordId));
    }

    function _permissionKey(
        string memory patientId,
        string memory doctorId,
        string memory recordId
    ) internal pure returns (bytes32) {
        return keccak256(
            abi.encodePacked(patientId, "|", doctorId, "|", recordId)
        );
    }

    function createRecord(
        string memory recordId,
        string memory patientId,
        string memory doctorId,
        string memory title,
        bytes32 recordHash
    ) external onlyOwner {
        bytes32 key = _recordKey(recordId);

        require(!records[key].exists, "Record already exists");

        records[key] = Record({
            recordId: recordId,
            patientId: patientId,
            doctorId: doctorId,
            title: title,
            recordHash: recordHash,
            createdAt: block.timestamp,
            exists: true
        });

        recordKeys.push(key);

        emit RecordCreated(
            recordId,
            patientId,
            doctorId,
            recordHash,
            block.timestamp
        );
    }

    function grantAccess(
        string memory patientId,
        string memory doctorId,
        string memory recordId,
        uint256 durationHours
    ) external onlyOwner {
        bytes32 recordKey = _recordKey(recordId);

        require(records[recordKey].exists, "Record does not exist");
        require(
            keccak256(bytes(records[recordKey].patientId)) ==
                keccak256(bytes(patientId)),
            "Patient does not own this record"
        );

        uint256 validUntil = block.timestamp + (durationHours * 1 hours);

        bytes32 permissionKey = _permissionKey(
            patientId,
            doctorId,
            recordId
        );

        permissions[permissionKey] = Permission({
            validUntil: validUntil,
            granted: true
        });

        emit AccessGranted(recordId, patientId, doctorId, validUntil);
    }

    function revokeAccess(
        string memory patientId,
        string memory doctorId,
        string memory recordId
    ) external onlyOwner {
        bytes32 permissionKey = _permissionKey(
            patientId,
            doctorId,
            recordId
        );

        permissions[permissionKey] = Permission({
            validUntil: 0,
            granted: false
        });

        emit AccessRevoked(recordId, patientId, doctorId);
    }

    function checkPermission(
        string memory patientId,
        string memory doctorId,
        string memory recordId
    ) public view returns (bool) {
        bytes32 permissionKey = _permissionKey(
            patientId,
            doctorId,
            recordId
        );

        Permission memory permission = permissions[permissionKey];

        return permission.granted && block.timestamp <= permission.validUntil;
    }

    function getRecord(
        string memory recordId
    )
        external
        view
        returns (
            string memory,
            string memory,
            string memory,
            string memory,
            bytes32,
            uint256,
            bool
        )
    {
        Record memory record = records[_recordKey(recordId)];

        require(record.exists, "Record does not exist");

        return (
            record.recordId,
            record.patientId,
            record.doctorId,
            record.title,
            record.recordHash,
            record.createdAt,
            record.exists
        );
    }

    function getRecordCount() external view returns (uint256) {
        return recordKeys.length;
    }

    function getRecordByIndex(uint256 index)
        external
        view
        returns (
            string memory,
            string memory,
            string memory,
            string memory,
            bytes32,
            uint256,
            bool
        )
    {
        require(index < recordKeys.length, "Index out of bounds");

        Record memory record = records[recordKeys[index]];

        return (
            record.recordId,
            record.patientId,
            record.doctorId,
            record.title,
            record.recordHash,
            record.createdAt,
            record.exists
        );
    }
}
