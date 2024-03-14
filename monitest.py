import okx.Account as Account
api_key = "e1b9fa18-438f-4186-8679-2e1a31cac369"
secret_key = "ED6A1408691C36597446782AA57D8BC3"
passphrase = "Llz0102!!"

flag = "1"  # live trading: 0, demo trading: 1
accountAPI = Account.AccountAPI(api_key, secret_key, passphrase, False, flag)
result = accountAPI.get_account_balance()
print(result)
