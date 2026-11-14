const hre = require("hardhat");
     const fs = require("fs");

     async function main() {
       const LandRegistry = await hre.ethers.getContractFactory("LandRegistry");
       const abi = LandRegistry.interface.formatJson();
       fs.writeFileSync("D:/THEO/blockland/abi.json", abi);
       console.log("✅ ABI saved to D:/THEO/blockland/abi.json");
     }

     main().catch((error) => {
       console.error("❌ ABI export failed:", error);
       process.exitCode = 1;
     });