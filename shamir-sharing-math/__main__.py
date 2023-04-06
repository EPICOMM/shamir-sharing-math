from .boolean import BooleanNode
from . import *

a = BooleanNode.or_(
    BooleanNode.and_(BooleanNode.var("x"), BooleanNode.var("a")),
    BooleanNode.and_(BooleanNode.var("x"), BooleanNode.var("b")),
    BooleanNode.and_(BooleanNode.var("x"), BooleanNode.var("c")),
    BooleanNode.thresh(2, BooleanNode.var("q"), BooleanNode.var("w"), BooleanNode.var("e")),
)
print('Splitting:')
c = Configuration(scheme=Scheme.COMPLEX, modulo=257, formula=a)
parts = c.split(123)
print(parts)

print('\nRestoring:')
parts = [parts[0], parts[1]]
print(parts)
secret = c.restore(parts)
print('=', secret)
