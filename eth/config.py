import os

class Config():
    SERVER = os.getenv('ETH_SERVER', 'localhost:8545')
    GAS_PAYER = os.getenv('ETH_GAS_PAYER')
    GAS = os.getenv('ETH_GAS')
    CONTRACT_URLS = [
        'https://raw.githubusercontent.com/hCaptcha/hmt-escrow/master/contracts/Escrow.sol',
        'https://raw.githubusercontent.com/hCaptcha/hmt-escrow/master/contracts/EscrowFactory.sol',
        'https://raw.githubusercontent.com/hCaptcha/hmt-escrow/master/contracts/HMToken.sol',
        'https://raw.githubusercontent.com/hCaptcha/hmt-escrow/master/contracts/HMTokenInterface.sol',
        'https://raw.githubusercontent.com/hCaptcha/hmt-escrow/master/contracts/SafeMath.sol',
    ]
