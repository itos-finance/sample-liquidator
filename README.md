# Super Simple Event Listener

## To run
`python3 main.py <pm_address> <resolver_address> <liquidator_contract_address> -p 4321`

## To call liquidate:
`http://localhost:4321/liquidate/<user_address>/<flashloan_scalar>/<simple_mode>`  

`flashloan_scalar` can be increased if not enough token is being flash loaned  
`simple-mode` can be set to True to simplify the resolution process and flashloan most tokens. Setting to false will try and swap out the tokens recieved in close taker, but is still lightly tested
