import os
import difflib
import re
from bs4 import BeautifulSoup

from database import Database
from request import Request

class Parser:
    def __init__(self, db):
        self.db = db
        self.recipes_quantity = 1

    def parseIngredients(self):
        request = Request('https://eda.ru/api/v2/graphql')
        offset = 0

        self.db.delete('ingredients')

        print("\nBeginning of ingredients parsing")

        while True:
            response = request.sendPost(
                '',
                {
                    "variables": {},
                    "query": f"{{ingredients(request: {{offset: {offset}, first: 100, sortField: RELEVANCE, sortDirection: DESC}}) {{  edges {{    node {{      id      name      accusativeCase      instrumentalCase      genitiveCase      relativeUrl      recipeRelativeUrl      shortDescription      recipesCount      slug      catalogPhoto      __typename    }}    __typename  }}  totalCount  pageInfo {{    hasNextPage    __typename  }}  __typename}}\n}}"
                }
            )

            if response:
                data = response.json()
                ingredients = data['data']['ingredients']['edges']

                if not ingredients:
                    break

                for ingredient in ingredients:
                    ingredient = ingredient['node']

                    self.db.create(
                        'ingredients',
                        {
                            'id':  ingredient['id'],
                            'name': ingredient['name'],
                            'description': ingredient['shortDescription'],
                            'slug': ingredient['slug'],
                        }
                    )

                print(f"{offset + len(ingredients)} ingredients are saved")

                offset += 100
            else:
                break

        print("\nFinishing of ingredients parsing")

    def parseRecipes1(self):
        request = Request('https://eda.ru/api/v2/graphql')
        offset = 0

        print("\nBeginning of recipes parsing with 'eda.ru'")

        self.db.delete(
            'recipes',
            {
                'source': ('=', 1)
            }
        )

        while True:
            response = request.sendPost(
                '',
                {
                    "variables": {},
                    "query": "{recipes(  request: {offset: " + str(offset) + ", first: 100, sortField: RELEVANCE, sortDirection: DESC, isEditorChoice: false}) {  edges {    node {      id      name      createUser {        fullName        id        photo        personalProps {          isFollowed          __typename        }        __typename      }      recipeCover {        id        createUser {          fullName          id          photo          __typename        }        imageUrl        imageLink {          url          folder          kind          __typename        }        isRecipeCover        createDate        likes        personalProps {          isLiked          __typename        }        __typename      }      composition {        amount        ingredient {          name          id          recipeRelativeUrl          __typename        }        measureUnit {          name          nameFive          nameTwo          __typename        }        __typename      }      slug      relativeUrl      videoFileId      createDate      videoFile {        id        videoId        videoUuid        coverUrl        duration        createDate        __typename      }      recipeCategory {        name        slug        __typename      }      cuisine {        name        slug        __typename      }      portionsCount      preparationTime      cookingTime      likes      dislikes      inCookbookCount      isSpecialProject      isEditorChoice      isGold1000      commentsCount      rootCommentsCount      navigationTags {        id        name        slug        __typename      }      aggregateRating {        bestRating        ratingValue        reviewCount        worstRating        __typename      }      personalProps {        isInCookbook        isLiked        isDisliked        cookMenuIds        __typename      }      recipeSteps {        description        imageUrl        id        __typename      }      nutritionInfo {        carbohydrates        fats        kilocalories        proteins        __typename      }      __typename    }    __typename  }  totalCount  pageInfo {    hasNextPage    __typename  }  __typename}}"
                }
            )
            
            if response:
                data = response.json()
                recipes = data['data']['recipes']['edges']

                if not recipes:
                    break

                for recipe in recipes:
                    recipe = recipe['node']
                    composition = []
                    steps = []

                    for ingredient in recipe['composition']:
                        composition.append(
                            {
                                'ingredient': ingredient['ingredient']['id'],
                                'amount': round(ingredient['amount'] / recipe['portionsCount'], 1),
                                'measure': ingredient['measureUnit']['name']
                            }
                        )

                    for step in recipe['recipeSteps']:
                        steps.append(step['description'])

                    self.insertRecipe(
                        {
                            'name': recipe['name'],
                            'image': 'image_url',
                            # 'image': self.saveImage(recipe['recipeCover']['imageUrl']),
                            'category': recipe['recipeCategory']['slug'],
                            'cuisine': recipe['cuisine']['slug'] if recipe['cuisine'] != None else '',
                            'cooking_time': recipe['cookingTime'],
                            'steps': steps,
                            'carbohydrates': recipe['nutritionInfo']['carbohydrates'],
                            'fats': recipe['nutritionInfo']['fats'],
                            'kilocalories': recipe['nutritionInfo']['kilocalories'],
                            'proteins': recipe['nutritionInfo']['proteins'],
                            'source': 1,
                            'composition': composition
                        }
                    )

                    print(f"{self.recipes_quantity} recipes are saved")
                    self.recipes_quantity+=1
                
                offset += 100
            else:
                break

        print("\nFinishing of recipes parsing with 'eda.ru'")

    def parseRecipes2(self):
        request = Request('https://api.food.ru/content/v2/')
        page = 1

        print("\nBeginning of recipes parsing with 'food.ru'")

        self.db.delete(
            'recipes',
            {
                'source': ('=', 2)
            }
        )

        while True:
            response = request.sendGet(
                'search',
                {
                    'page': page,
                    'max_per_page': 100,
                    'material': 'recipe',
                    'format': 'json'
                }
            )

            if response:
                data = response.json()
                recipes = data['materials']

                for recipe in recipes:
                    parse_request = Request(f'https://www.food.ru/recipes/{recipe['id']}-{recipe['url_part']}')

                    response = parse_request.sendGet()

                    if response.status_code == 200:
                        composition = []
                        steps = []
                        soup = BeautifulSoup(response.content, 'html.parser')

                        for ingredient in soup.find_all(class_='ingredient'):
                            id = None
                            amount = 0
                            measure = ''

                            if self.findSimilarIngredients(ingredient.find(class_='name').text.strip()) != None: 
                                id = self.findSimilarIngredients(ingredient.find(class_='name').text.strip())[0]
                            else:
                                id = self.insertIngredient(ingredient.find(class_='name').text.strip())

                            if ingredient.find(class_ = 'value') != None :
                                amount = float(ingredient.find(class_ = 'value').text.strip()) / int(soup.find(class_ = 'selectNumberOfServing_input__o9Mdl').input.get('value'))

                            if ingredient.find(class_= 'type') != None :
                                measure = ingredient.find(class_ = 'type').text.strip()

                            composition.append({
                                'ingredient': id,
                                'amount': amount,
                                'measure': measure
                            })
                        
                        for step in soup.find_all(class_='stepByStepPhotoRecipe_step__ygqQw'):
                            steps.append(step.find(class_ = 'markup_text__F9WKe').text.strip())

                        self.insertRecipe({
                                'name': recipe['main_title'],
                                'image': 'image_url',
                                #'image': self.saveImage(soup.find(attrs = {'itemprop': 'url'}).get('href')),
                                'category': soup.find_all(class_ = 'breadcrumbs_text__gFKWC')[1].text.strip(),
                                'cuisine': soup.find(attrs = {'itemprop': 'recipeCuisine'}).get('content'),
                                'cooking_time': recipe['total_cooking_time'],
                                'steps': steps,
                                'carbohydrates': soup.find_all(class_ = 'nutrient_value__dd48k')[3].text.strip(),
                                'fats': soup.find_all(class_ = 'nutrient_value__dd48k')[2].text.strip(),
                                'kilocalories': soup.find_all(class_ = 'nutrient_value__dd48k')[0].text.strip(),
                                'proteins': soup.find_all(class_ = 'nutrient_value__dd48k')[1].text.strip(),
                                'source': 2,
                                'composition': composition
                        })

                    print(f"{self.recipes_quantity} recipes are saved")
                    self.recipes_quantity+=1
            else:
                break

            # page += 1 
            break

        print("\nFinishing of recipes parsing with 'food.ru'")

    def parseAll(self):
        self.parseIngredients()
        self.parseRecipes1()
        self.parseRecipes2()
  
    def findSimilarIngredients(self, ingredient):  
        similar_ingredients = self.db.get(
            'ingredients',
            'id, name',
            {
                '_fulltext': (
                    'ingredients.name',
                    ingredient + ' '.join(f'+*{word}*' for word in ingredient.split()),
                    'boolean'
                )
            },
            options = {
                'limit': 10
            }
        )

        if not similar_ingredients:
            return None
        
        ingredient_names = [ing[1] for ing in similar_ingredients]
        best_match = difflib.get_close_matches(ingredient, ingredient_names, 1)

        if best_match:
            return next(ing for ing in similar_ingredients if ing[1] == best_match[0])
        else:
            return None

    def insertIngredient(self, ingredient): 
        return self.db.create(
            'ingredients',
            {
                'name': ingredient,
                'description': '',
                'slug': self.createSlug(ingredient),
            }
        )

    def insertRecipe(self, recipe): 
        id = self.db.create(
            'recipes',
            {
                'name': recipe['name'],
                'image': recipe['image'],
                'category': recipe['category'],
                'cuisine': recipe['cuisine'],
                'cooking_time': recipe['cooking_time'],
                'carbohydrates': recipe['carbohydrates'],
                'fats': recipe['fats'],
                'kilocalories': recipe['kilocalories'],
                'proteins': recipe['proteins'],
                'source': recipe['source']
            }
        )

        for ingredient in recipe['composition']:
            self.db.create(
                'recipes_ingredients',
                {
                    'recipe': id,
                    'ingredient': ingredient['ingredient'],
                    'amount': ingredient['amount'],
                    'measure': ingredient['measure']
                }
            )
        
        for step in recipe['steps']:
            self.db.create(
                'recipes_steps',
                {
                    'recipe': id,
                    'text': step,
                }
            )

    def createSlug(self, title):
        translit_dict = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo', 'ж': 'zh', 'з': 'z', 'и': 'i',
            'й': 'j', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
            'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ъ': '', 'ы': 'y', 'ь': '',
            'э': 'e', 'ю': 'yu', 'я': 'ya',
            'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo', 'Ж': 'Zh', 'З': 'Z', 'И': 'I',
            'Й': 'J', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T',
            'У': 'U', 'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shch', 'Ъ': '', 'Ы': 'Y', 'Ь': '',
            'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
        }

        translit_title = ''.join(translit_dict.get(char, char) for char in title)
        translit_title = translit_title.lower()
        slug = re.sub(r'[^a-z0-9]+', '-', translit_title)
        return slug.strip('-')

    def saveImage(self, url):
        if not os.path.exists('images'):
            os.makedirs('images')

        response = Request(url).sendGet()

        if response.status_code == 200:
            extension = os.path.splitext(url)[1]

            filename = f"image_{len(os.listdir('images')) + 1}{extension}"

            with open(os.path.join('images', filename), 'wb') as f:
                f.write(response.content)

            return filename
        else:
            return None