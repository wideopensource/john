from sys import exit

from john import Factory


def demo() -> int:
    john = Factory().create_John()
    
    print(f'{john} should be None')

    return 42

if '__main__' == __name__:

    exit(demo())
