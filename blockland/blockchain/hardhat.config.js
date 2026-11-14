// blockchain/hardhat.config.js
require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

module.exports = {
  solidity: "0.8.9", // Match your contract version
  networks: {
    ganache: {
      url: "http://127.0.0.1:7545",
      chainId: 1337,
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : "remote",
    },
  },
};
// require("@nomicfoundation/hardhat-toolbox");
// require("dotenv").config();

// module.exports = {
//   solidity: "0.8.9",
//   networks: {
//     sepolia: {
//       url: process.env.ALCHEMY_SEPOLIA_URL,
//       accounts: [process.env.PRIVATE_KEY]
//     }
//   },
//   etherscan: {
//     apiKey: {
//       sepolia: process.env.ETHERSCAN_API_KEY
//     }
//   }
// };

// require("@nomicfoundation/hardhat-toolbox");
// /** @type import('hardhat/config').HardhatUserConfig */
// require("dotenv").config();

// module.exports = {
//   solidity: "0.8.9",
//   networks: {
//     hardhat: {},
//     sepolia: {
//       url: process.env.ALCHEMY_SEPOLIA_URL || "https://eth-sepolia.g.alchemy.com/v2/FXgsq3SBhlaAljbW92pY3",
//       accounts: [process.env.PRIVATE_KEY || "ef765693569d914af4c30e98d2b5a8286ab2e83dd53895d5317f9681b238c080"]
//     }
//   }
// };
