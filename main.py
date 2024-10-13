from database import Database
from parser import Parser

db = Database('localhost', 'recipes', 'root', '')
parser = Parser(db)

# print(parser.findSimilarIngredients(input()))
parser.parseRecipes2()

db.close()