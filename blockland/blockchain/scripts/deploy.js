const hre = require("hardhat");
     const fs = require("fs");

     async function main() {
       // ✅ Check the network and chain ID before deployment
       const network = await hre.ethers.provider.getNetwork();
       console.log("✅ Using Network:", network.name);
       console.log("✅ Chain ID:", network.chainId);

       // ✅ Deploy the contract
       const LandRegistry = await hre.ethers.getContractFactory("LandRegistry");
       const landRegistry = await LandRegistry.deploy();

       await landRegistry.waitForDeployment();
       const contractAddress = await landRegistry.getAddress();
       console.log("✅ LandRegistry deployed to:", contractAddress);

       // ✅ Save contract address for .env
       console.log(`Update your .env with: CONTRACT_ADDRESS=${contractAddress}`);

       // ✅ Save ABI for Django app
       const abi = LandRegistry.interface.formatJson();
       fs.writeFileSync("D:/THEO/blockland/abi.json", abi);
       console.log("✅ ABI saved to D:/THEO/blockland/abi.json");
     }

     main().catch((error) => {
       console.error("❌ Deployment failed:", error);
       process.exitCode = 1;
     });