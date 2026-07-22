import random
import string


def get_random_string(length: int = 10) -> str:
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))





if __name__ == "__main__":
    print("utils file")
    

    
    
    