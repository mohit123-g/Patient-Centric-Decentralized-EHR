const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  const Factory = await hre.ethers.getContractFactory("PatientEHR");
  const contract = await Factory.deploy();
  await contract.waitForDeployment();

  const address = await contract.getAddress();
  const [deployer] = await hre.ethers.getSigners();

  const deployment = {
    address,
    deployer: deployer.address,
    network: "localhost",
    chainId: 31337,
    deployedAt: new Date().toISOString()
  };

  fs.writeFileSync(
    path.join(__dirname, "..", "deployment.json"),
    JSON.stringify(deployment, null, 2)
  );

  console.log("PatientEHR deployed to:", address);
  console.log("Deployer:", deployer.address);
  console.log("Saved deployment.json");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
