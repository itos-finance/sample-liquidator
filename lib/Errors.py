# Exception raised when token is not in the token registry. Resolver owner needs to add the token. If you are
# not the owner, you may also deploy your own resolver. Please see the Itos docs for how to do this. TODO add link
class TokenNotInResolverRegistry(Exception):
    pass

if __name__ == "__main__":
    pass