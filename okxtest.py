import okx.Account as Account

# API initialization
apikey = "9cdc7713-03f3-4caa-8b72-1df7dda5e5bd"
secretkey = "5113559E17688A2FF24FA1ECD74D4A07"
passphrase = "Zmt19960425!"

flag = "0"  # Production trading:0 , demo trading:1

accountAPI = Account.AccountAPI(apikey, secretkey, passphrase, False, flag)

# Get account balance
result = accountAPI.get_account_balance()
print(result)
 