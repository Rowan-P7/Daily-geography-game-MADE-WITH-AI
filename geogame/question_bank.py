import hashlib
import json
import random


# The country facts below use stable reference facts; question records are
# generated from this seed so the bank remains straightforward to extend.
COUNTRIES = [
    ("Algeria", "Algiers", "Algerian dinar", "Africa", "🇩🇿"),
    ("Angola", "Luanda", "Angolan kwanza", "Africa", "🇦🇴"),
    ("Botswana", "Gaborone", "Botswana pula", "Africa", "🇧🇼"),
    ("Cameroon", "Yaoundé", "Central African CFA franc", "Africa", "🇨🇲"),
    ("Democratic Republic of the Congo", "Kinshasa", "Congolese franc", "Africa", "🇨🇩"),
    ("Egypt", "Cairo", "Egyptian pound", "Africa", "🇪🇬"),
    ("Ethiopia", "Addis Ababa", "Ethiopian birr", "Africa", "🇪🇹"),
    ("Ghana", "Accra", "Ghanaian cedi", "Africa", "🇬🇭"),
    ("Kenya", "Nairobi", "Kenyan shilling", "Africa", "🇰🇪"),
    ("Madagascar", "Antananarivo", "Malagasy ariary", "Africa", "🇲🇬"),
    ("Morocco", "Rabat", "Moroccan dirham", "Africa", "🇲🇦"),
    ("Mozambique", "Maputo", "Mozambican metical", "Africa", "🇲🇿"),
    ("Namibia", "Windhoek", "Namibian dollar", "Africa", "🇳🇦"),
    ("Nigeria", "Abuja", "Nigerian naira", "Africa", "🇳🇬"),
    ("Senegal", "Dakar", "West African CFA franc", "Africa", "🇸🇳"),
    ("South Africa", "Pretoria", "South African rand", "Africa", "🇿🇦"),
    ("Tanzania", "Dodoma", "Tanzanian shilling", "Africa", "🇹🇿"),
    ("Tunisia", "Tunis", "Tunisian dinar", "Africa", "🇹🇳"),
    ("Uganda", "Kampala", "Ugandan shilling", "Africa", "🇺🇬"),
    ("Zimbabwe", "Harare", "Zimbabwe Gold (ZiG)", "Africa", "🇿🇼"),
    ("Afghanistan", "Kabul", "Afghan afghani", "Asia", "🇦🇫"),
    ("Bangladesh", "Dhaka", "Bangladeshi taka", "Asia", "🇧🇩"),
    ("Cambodia", "Phnom Penh", "Cambodian riel", "Asia", "🇰🇭"),
    ("China", "Beijing", "Chinese yuan", "Asia", "🇨🇳"),
    ("India", "New Delhi", "Indian rupee", "Asia", "🇮🇳"),
    ("Indonesia", "Jakarta", "Indonesian rupiah", "Asia", "🇮🇩"),
    ("Iran", "Tehran", "Iranian rial", "Asia", "🇮🇷"),
    ("Iraq", "Baghdad", "Iraqi dinar", "Asia", "🇮🇶"),
    ("Japan", "Tokyo", "Japanese yen", "Asia", "🇯🇵"),
    ("Jordan", "Amman", "Jordanian dinar", "Asia", "🇯🇴"),
    ("Kazakhstan", "Astana", "Kazakhstani tenge", "Asia", "🇰🇿"),
    ("Malaysia", "Kuala Lumpur", "Malaysian ringgit", "Asia", "🇲🇾"),
    ("Mongolia", "Ulaanbaatar", "Mongolian tögrög", "Asia", "🇲🇳"),
    ("Nepal", "Kathmandu", "Nepalese rupee", "Asia", "🇳🇵"),
    ("Pakistan", "Islamabad", "Pakistani rupee", "Asia", "🇵🇰"),
    ("Philippines", "Manila", "Philippine peso", "Asia", "🇵🇭"),
    ("Saudi Arabia", "Riyadh", "Saudi riyal", "Asia", "🇸🇦"),
    ("Singapore", "Singapore", "Singapore dollar", "Asia", "🇸🇬"),
    ("South Korea", "Seoul", "South Korean won", "Asia", "🇰🇷"),
    ("Thailand", "Bangkok", "Thai baht", "Asia", "🇹🇭"),
    ("Vietnam", "Hanoi", "Vietnamese đồng", "Asia", "🇻🇳"),
    ("Austria", "Vienna", "Euro", "Europe", "🇦🇹"),
    ("Belgium", "Brussels", "Euro", "Europe", "🇧🇪"),
    ("Croatia", "Zagreb", "Euro", "Europe", "🇭🇷"),
    ("Czechia", "Prague", "Czech koruna", "Europe", "🇨🇿"),
    ("Denmark", "Copenhagen", "Danish krone", "Europe", "🇩🇰"),
    ("Finland", "Helsinki", "Euro", "Europe", "🇫🇮"),
    ("France", "Paris", "Euro", "Europe", "🇫🇷"),
    ("Germany", "Berlin", "Euro", "Europe", "🇩🇪"),
    ("Greece", "Athens", "Euro", "Europe", "🇬🇷"),
    ("Iceland", "Reykjavík", "Icelandic króna", "Europe", "🇮🇸"),
    ("Ireland", "Dublin", "Euro", "Europe", "🇮🇪"),
    ("Italy", "Rome", "Euro", "Europe", "🇮🇹"),
    ("Netherlands", "Amsterdam", "Euro", "Europe", "🇳🇱"),
    ("Norway", "Oslo", "Norwegian krone", "Europe", "🇳🇴"),
    ("Poland", "Warsaw", "Polish złoty", "Europe", "🇵🇱"),
    ("Portugal", "Lisbon", "Euro", "Europe", "🇵🇹"),
    ("Romania", "Bucharest", "Romanian leu", "Europe", "🇷🇴"),
    ("Spain", "Madrid", "Euro", "Europe", "🇪🇸"),
    ("Sweden", "Stockholm", "Swedish krona", "Europe", "🇸🇪"),
    ("Switzerland", "Bern", "Swiss franc", "Europe", "🇨🇭"),
    ("Ukraine", "Kyiv", "Ukrainian hryvnia", "Europe", "🇺🇦"),
    ("United Kingdom", "London", "Pound sterling", "Europe", "🇬🇧"),
    ("Canada", "Ottawa", "Canadian dollar", "North America", "🇨🇦"),
    ("Costa Rica", "San José", "Costa Rican colón", "North America", "🇨🇷"),
    ("Cuba", "Havana", "Cuban peso", "North America", "🇨🇺"),
    ("Dominican Republic", "Santo Domingo", "Dominican peso", "North America", "🇩🇴"),
    ("El Salvador", "San Salvador", "United States dollar", "North America", "🇸🇻"),
    ("Guatemala", "Guatemala City", "Guatemalan quetzal", "North America", "🇬🇹"),
    ("Haiti", "Port-au-Prince", "Haitian gourde", "North America", "🇭🇹"),
    ("Honduras", "Tegucigalpa", "Honduran lempira", "North America", "🇭🇳"),
    ("Jamaica", "Kingston", "Jamaican dollar", "North America", "🇯🇲"),
    ("Mexico", "Mexico City", "Mexican peso", "North America", "🇲🇽"),
    ("Panama", "Panama City", "United States dollar", "North America", "🇵🇦"),
    ("United States", "Washington, D.C.", "United States dollar", "North America", "🇺🇸"),
    ("Argentina", "Buenos Aires", "Argentine peso", "South America", "🇦🇷"),
    ("Bolivia", "Sucre", "Bolivian boliviano", "South America", "🇧🇴"),
    ("Brazil", "Brasília", "Brazilian real", "South America", "🇧🇷"),
    ("Chile", "Santiago", "Chilean peso", "South America", "🇨🇱"),
    ("Colombia", "Bogotá", "Colombian peso", "South America", "🇨🇴"),
    ("Ecuador", "Quito", "United States dollar", "South America", "🇪🇨"),
    ("Guyana", "Georgetown", "Guyanese dollar", "South America", "🇬🇾"),
    ("Paraguay", "Asunción", "Paraguayan guaraní", "South America", "🇵🇾"),
    ("Peru", "Lima", "Peruvian sol", "South America", "🇵🇪"),
    ("Suriname", "Paramaribo", "Surinamese dollar", "South America", "🇸🇷"),
    ("Uruguay", "Montevideo", "Uruguayan peso", "South America", "🇺🇾"),
    ("Venezuela", "Caracas", "Venezuelan bolívar", "South America", "🇻🇪"),
    ("Australia", "Canberra", "Australian dollar", "Oceania", "🇦🇺"),
    ("Fiji", "Suva", "Fijian dollar", "Oceania", "🇫🇯"),
    ("New Zealand", "Wellington", "New Zealand dollar", "Oceania", "🇳🇿"),
    ("Papua New Guinea", "Port Moresby", "Papua New Guinean kina", "Oceania", "🇵🇬"),
    ("Samoa", "Apia", "Samoan tālā", "Oceania", "🇼🇸"),
    ("Solomon Islands", "Honiara", "Solomon Islands dollar", "Oceania", "🇸🇧"),
    ("Tonga", "Nukuʻalofa", "Tongan paʻanga", "Oceania", "🇹🇴"),
    ("Vanuatu", "Port Vila", "Vanuatu vatu", "Oceania", "🇻🇺"),
]

GEOGRAPHY = [
    ("Which mountain is Earth's highest above sea level?", "Physical geography", "Mount Everest", ["K2", "Mount Kilimanjaro", "Denali"], "Mount Everest", "Mount Everest reaches 8,849 metres above sea level in the Himalayas."),
    ("Which is the largest ocean on Earth?", "Physical geography", "Pacific Ocean", ["Atlantic Ocean", "Indian Ocean", "Arctic Ocean"], "Pacific Ocean", "The Pacific is the largest and deepest ocean."),
    ("Which river flows through the Amazon rainforest?", "Physical geography", "Amazon River", ["Orinoco", "Paraná", "São Francisco"], "Amazon River", "The Amazon River and its tributaries drain a vast area of South America."),
    ("Which desert is the world's largest hot desert?", "Physical geography", "Sahara Desert", ["Gobi Desert", "Kalahari Desert", "Atacama Desert"], "Sahara Desert", "The Sahara spans much of North Africa."),
    ("Which is the world's largest island, excluding continents?", "Physical geography", "Greenland", ["Borneo", "Madagascar", "New Guinea"], "Greenland", "Greenland is the largest island that is not considered a continent."),
    ("Which country contains the Great Barrier Reef?", "Landmarks", "Australia", ["Fiji", "Indonesia", "Papua New Guinea"], "Australia", "The Great Barrier Reef lies off the northeastern coast of Australia."),
    ("Machu Picchu is an archaeological site in which country?", "Landmarks", "Peru", ["Bolivia", "Ecuador", "Chile"], "Peru", "Machu Picchu is a 15th-century Inca site in the Peruvian Andes."),
    ("The ancient city of Petra is in which country?", "Landmarks", "Jordan", ["Egypt", "Lebanon", "Syria"], "Jordan", "Petra is an archaeological city in southern Jordan."),
    ("Which city is home to the Eiffel Tower?", "Landmarks", "Paris", ["Rome", "Brussels", "Madrid"], "Paris", "The Eiffel Tower is a landmark in the French capital."),
    ("The Taj Mahal is located in which Indian city?", "Landmarks", "Agra", ["Jaipur", "Delhi", "Mumbai"], "Agra", "The Taj Mahal stands in Agra, in the Indian state of Uttar Pradesh."),
    ("Which is the world's smallest independent country by area?", "World records", "Vatican City", ["Monaco", "San Marino", "Liechtenstein"], "Vatican City", "Vatican City is the smallest sovereign state by area."),
    ("Which is the largest country in the world by area?", "World records", "Russia", ["Canada", "China", "United States"], "Russia", "Russia spans eastern Europe and northern Asia and is the world's largest country by area."),
    ("Which strait separates Spain and Morocco?", "Borders & regions", "Strait of Gibraltar", ["Bosporus", "Dover Strait", "Bering Strait"], "Strait of Gibraltar", "The Strait of Gibraltar connects the Atlantic Ocean and Mediterranean Sea."),
    ("Which two countries share the longest international land border?", "Borders & regions", "Canada and the United States", ["Russia and China", "Argentina and Chile", "India and Bangladesh"], "Canada and the United States", "The Canada–United States border is the longest international land border."),
    ("Which sea lies between northeastern Africa and the Arabian Peninsula?", "Physical geography", "Red Sea", ["Black Sea", "Arabian Sea", "Caspian Sea"], "Red Sea", "The Red Sea separates Africa from the Arabian Peninsula."),
    ("On which continent is the Andes mountain range?", "Physical geography", "South America", ["Africa", "Asia", "Europe"], "South America", "The Andes run along the western edge of South America."),
    ("Which African country is completely surrounded by South Africa?", "Borders & regions", "Lesotho", ["Eswatini", "Botswana", "Namibia"], "Lesotho", "Lesotho is an enclaved country entirely surrounded by South Africa."),
    ("Which lake is the world's deepest freshwater lake?", "World records", "Lake Baikal", ["Lake Superior", "Lake Tanganyika", "Lake Victoria"], "Lake Baikal", "Lake Baikal in Russia reaches about 1,642 metres in depth."),
    ("Which is the largest lake in Africa by surface area?", "Physical geography", "Lake Victoria", ["Lake Tanganyika", "Lake Malawi", "Lake Chad"], "Lake Victoria", "Lake Victoria is Africa's largest lake by surface area."),
    ("The world's highest uninterrupted waterfall, Angel Falls, is in which country?", "Landmarks", "Venezuela", ["Brazil", "Colombia", "Guyana"], "Venezuela", "Angel Falls drops from Auyán-tepui in Venezuela's Canaima National Park."),
    ("Which ocean borders the east coast of the United States?", "Physical geography", "Atlantic Ocean", ["Pacific Ocean", "Indian Ocean", "Arctic Ocean"], "Atlantic Ocean", "The Atlantic Ocean lies east of the contiguous United States."),
    ("Which country is home to Mount Fuji?", "Physical geography", "Japan", ["South Korea", "China", "Indonesia"], "Japan", "Mount Fuji is a volcanic mountain on Japan's Honshu Island."),
    ("Which desert covers much of Botswana and Namibia?", "Physical geography", "Kalahari Desert", ["Sahara Desert", "Namib Desert", "Danakil Desert"], "Kalahari Desert", "The Kalahari is a large sandy savanna region in southern Africa."),
    ("Which river runs through London?", "Physical geography", "River Thames", ["River Severn", "River Clyde", "River Trent"], "River Thames", "London grew around the River Thames in southeastern England."),
    ("Which country has the most natural lakes?", "World records", "Canada", ["Finland", "Russia", "United States"], "Canada", "Canada has more natural lakes than any other country."),
    ("Which mountain range traditionally marks part of the boundary between Europe and Asia?", "Physical geography", "Ural Mountains", ["Alps", "Carpathians", "Pyrenees"], "Ural Mountains", "The Ural Mountains are a conventional geographic boundary between Europe and Asia."),
    ("Which country contains the ancient city of Angkor?", "Landmarks", "Cambodia", ["Thailand", "Laos", "Vietnam"], "Cambodia", "Angkor, including Angkor Wat, is a historic temple complex in Cambodia."),
    ("Which two countries share Lake Titicaca?", "Borders & regions", "Peru and Bolivia", ["Chile and Argentina", "Peru and Ecuador", "Bolivia and Paraguay"], "Peru and Bolivia", "Lake Titicaca lies on the border of Peru and Bolivia."),
    ("Which is the world's largest coral reef system?", "World records", "Great Barrier Reef", ["Belize Barrier Reef", "New Caledonia Barrier Reef", "Red Sea coral reef"], "Great Barrier Reef", "The Great Barrier Reef is the largest coral reef system, off Australia."),
    ("Which country is home to the ancient city of Timbuktu?", "Landmarks", "Mali", ["Niger", "Chad", "Mauritania"], "Mali", "Timbuktu is a historic city in central Mali, near the Niger River."),
]

LANGUAGES = [
    ("Which language is one of South Africa's official languages?", "Zulu", ["Swahili", "Amharic", "Wolof"]),
    ("Which language is an official language of Kenya alongside English?", "Swahili", ["Amharic", "Wolof", "Somali"]),
    ("Which language is one of Switzerland's national languages?", "German", ["Dutch", "Danish", "Polish"]),
    ("Which language is an official language of Canada?", "French", ["Spanish", "Portuguese", "Italian"]),
    ("Which language is one of Singapore's four official languages?", "Malay", ["Thai", "Khmer", "Burmese"]),
    ("Which language is an official language of Madagascar?", "Malagasy", ["Zulu", "Amharic", "Somali"]),
    ("Which language is an official language of Brazil?", "Portuguese", ["Spanish", "French", "Dutch"]),
    ("Which language is an official language of Egypt?", "Arabic", ["Amharic", "Berber", "Swahili"]),
    ("Which language is one of India's Union official languages?", "Hindi", ["Tamil", "Bengali", "Nepali"]),
    ("Which language is an official language of New Zealand?", "Māori", ["Samoan", "Tongan", "Fijian"]),
    ("Which language is an official language of Ireland?", "Irish", ["Welsh", "Scots", "Breton"]),
    ("Which language is an official language of Tanzania?", "Swahili", ["Amharic", "Hausa", "Yoruba"]),
    ("Which language is an official language of Morocco?", "Arabic", ["Swahili", "Amharic", "Hausa"]),
    ("Which language is an official language of the Philippines?", "Filipino", ["Malay", "Khmer", "Lao"]),
    ("Which language is an official language of Vietnam?", "Vietnamese", ["Thai", "Khmer", "Lao"]),
    ("Which language is an official language of Portugal?", "Portuguese", ["Spanish", "Italian", "French"]),
    ("Which language is an official language of Japan?", "Japanese", ["Korean", "Mandarin", "Mongolian"]),
    ("Which language is an official language of Greece?", "Greek", ["Albanian", "Bulgarian", "Turkish"]),
    ("Which language is an official language of Iceland?", "Icelandic", ["Norwegian", "Danish", "Swedish"]),
    ("Which language is widely spoken and an official language of Ethiopia?", "Amharic", ["Swahili", "Zulu", "Wolof"]),
]

POPULATIONS_2023 = [
    ("India", "about 1.4 billion", ["about 140 million", "about 400 million", "about 2.4 billion"]),
    ("China", "about 1.4 billion", ["about 140 million", "about 400 million", "about 2.4 billion"]),
    ("United States", "about 335 million", ["about 35 million", "about 135 million", "about 935 million"]),
    ("Indonesia", "about 280 million", ["about 80 million", "about 180 million", "about 580 million"]),
    ("Pakistan", "about 250 million", ["about 50 million", "about 150 million", "about 450 million"]),
    ("Nigeria", "about 230 million", ["about 30 million", "about 130 million", "about 430 million"]),
    ("Brazil", "about 215 million", ["about 15 million", "about 115 million", "about 515 million"]),
    ("Bangladesh", "about 170 million", ["about 70 million", "about 270 million", "about 370 million"]),
    ("Russia", "about 145 million", ["about 45 million", "about 245 million", "about 345 million"]),
    ("Mexico", "about 130 million", ["about 30 million", "about 230 million", "about 330 million"]),
    ("Japan", "about 125 million", ["about 25 million", "about 225 million", "about 325 million"]),
    ("Ethiopia", "about 130 million", ["about 30 million", "about 230 million", "about 330 million"]),
    ("Egypt", "about 115 million", ["about 15 million", "about 215 million", "about 315 million"]),
    ("Philippines", "about 115 million", ["about 15 million", "about 215 million", "about 315 million"]),
    ("Democratic Republic of the Congo", "about 105 million", ["about 5 million", "about 205 million", "about 305 million"]),
    ("Vietnam", "about 100 million", ["about 10 million", "about 200 million", "about 300 million"]),
    ("Iran", "about 90 million", ["about 9 million", "about 190 million", "about 290 million"]),
    ("Germany", "about 85 million", ["about 8 million", "about 185 million", "about 285 million"]),
    ("Thailand", "about 70 million", ["about 7 million", "about 170 million", "about 270 million"]),
    ("France", "about 68 million", ["about 18 million", "about 168 million", "about 268 million"]),
]

BORDERS = [
    ("Which country shares a land border with Portugal?", "Spain", ["France", "Italy", "Morocco"]),
    ("Which country shares a land border with the United States?", "Canada", ["Brazil", "Cuba", "Iceland"]),
    ("Which country shares a land border with Argentina?", "Chile", ["Ecuador", "Suriname", "Guyana"]),
    ("Which country shares a land border with Kenya?", "Tanzania", ["Nigeria", "Morocco", "Senegal"]),
    ("Which country shares a land border with Nepal?", "India", ["Thailand", "Malaysia", "Japan"]),
    ("Which country shares a land border with Thailand?", "Cambodia", ["Singapore", "Sri Lanka", "Japan"]),
    ("Which country shares a land border with Senegal?", "The Gambia", ["Ghana", "Morocco", "Cameroon"]),
    ("Which country shares a land border with Germany?", "Poland", ["Spain", "Portugal", "Ireland"]),
    ("Which country shares a land border with Colombia?", "Venezuela", ["Costa Rica", "El Salvador", "Jamaica"]),
    ("Which country shares a land border with Austria?", "Italy", ["Denmark", "Portugal", "Ireland"]),
    ("Which country shares a land border with Bolivia?", "Peru", ["Panama", "Venezuela", "Suriname"]),
    ("Which country shares a land border with Vietnam?", "China", ["Singapore", "Indonesia", "Philippines"]),
    ("Which country shares a land border with Morocco?", "Algeria", ["Ghana", "Ethiopia", "Angola"]),
    ("Which country shares a land border with Uganda?", "Kenya", ["Senegal", "Morocco", "Tunisia"]),
    ("Which country shares a land border with Poland?", "Czechia", ["Denmark", "Ireland", "Portugal"]),
    ("Which country shares a land border with Brazil?", "Peru", ["Costa Rica", "Haiti", "Jamaica"]),
    ("Which country shares a land border with Cambodia?", "Laos", ["Singapore", "Brunei", "Japan"]),
    ("Which country shares a land border with Greece?", "Bulgaria", ["Italy", "Cyprus", "Malta"]),
    ("Which country shares a land border with Ghana?", "Togo", ["Kenya", "Ethiopia", "Tunisia"]),
    ("Which country shares a land border with Finland?", "Sweden", ["United Kingdom", "Iceland", "Denmark"]),
]

MAP_QUESTIONS = [
    ("The marked point is at 22° S, 43° W. Which north-south half of Earth is it in?", -22, -43, "Southern Hemisphere", ["Northern Hemisphere", "Eastern Hemisphere", "Western Hemisphere"]),
    ("The marked point is at 1° N, 37° E. Which continent is it on?", 1, 37, "Africa", ["Asia", "Europe", "South America"]),
    ("The marked point is at 36° N, 140° E. Which continent is it on?", 36, 140, "Asia", ["Europe", "Africa", "Oceania"]),
    ("The marked point is at 52° N, 0° E. Which continent is it on?", 52, 0, "Europe", ["Asia", "North America", "Africa"]),
    ("The marked point is at 34° S, 151° E. Which continent is it on?", -34, 151, "Oceania", ["Africa", "South America", "Asia"]),
    ("The marked point is at 41° N, 74° W. Which continent is it on?", 41, -74, "North America", ["South America", "Europe", "Asia"]),
    ("The marked point is at 35° S, 58° W. Which continent is it on?", -35, -58, "South America", ["North America", "Africa", "Oceania"]),
    ("The marked point is at 30° N, 31° E. Which continent is it on?", 30, 31, "Africa", ["Asia", "Europe", "South America"]),
    ("The marked point is at 28° N, 87° E. Which continent is it on?", 28, 87, "Asia", ["Europe", "Africa", "North America"]),
    ("The marked point is at 0° latitude, 30° E. Which major line of latitude does it lie on?", 0, 30, "The Equator", ["Tropic of Cancer", "Tropic of Capricorn", "Arctic Circle"]),
    ("The marked point is at 64° N, 22° W. Which continent is it on?", 64, -22, "Europe", ["North America", "Asia", "Africa"]),
    ("The marked point is at 15° S, 47° W. Which continent is it on?", -15, -47, "South America", ["Africa", "Oceania", "North America"]),
]

NUMERICAL_ESTIMATES = [
    ("About how tall is Mount Everest above sea level?", 8849, 50, "m", "8,849 m", 7000, 10000, "Mount Everest reaches 8,849 metres above sea level."),
    ("About how tall is Mount Kilimanjaro?", 5895, 80, "m", "5,895 m", 4000, 7500, "Kilimanjaro's Uhuru Peak is 5,895 metres above sea level."),
    ("About how long is Earth's circumference at the Equator?", 40075, 1200, "km", "40,075 km", 20000, 60000, "Earth's equatorial circumference is about 40,075 kilometres."),
    ("About how large is the Sahara Desert?", 9200000, 1200000, "km²", "9.2 million km²", 5000000, 15000000, "The Sahara covers roughly 9.2 million square kilometres."),
    ("About how large is Australia by area?", 7692000, 700000, "km²", "7.7 million km²", 4000000, 12000000, "Australia covers about 7.7 million square kilometres."),
    ("About how deep is the Challenger Deep, the deepest known point in the ocean?", 10935, 500, "m", "10,935 m", 8000, 13000, "Challenger Deep is about 10,935 metres below sea level; measurements vary."),
    ("About how deep is Lake Baikal at its deepest point?", 1642, 180, "m", "1,642 m", 1000, 2500, "Lake Baikal reaches a maximum depth of about 1,642 metres."),
    ("About how large is the Pacific Ocean?", 165200000, 25000000, "km²", "165.2 million km²", 100000000, 220000000, "The Pacific Ocean covers about 165 million square kilometres."),
    ("About how large is Canada by area?", 9985000, 1000000, "km²", "10.0 million km²", 6000000, 15000000, "Canada covers just under 10 million square kilometres."),
    ("About how high is Angel Falls?", 979, 120, "m", "979 m", 500, 1500, "Angel Falls has a total height of about 979 metres."),
]


def build_questions():
    questions = []
    countries = [dict(name=c[0], capital=c[1], currency=c[2], continent=c[3], flag=c[4]) for c in COUNTRIES]
    all_names = [country["name"] for country in countries]
    all_capitals = [country["capital"] for country in countries]
    all_currencies = list(dict.fromkeys(country["currency"] for country in countries))
    all_continents = list(dict.fromkeys(country["continent"] for country in countries))

    def options_for(correct, pool, seed):
        alternatives = [item for item in pool if item != correct]
        random.Random(seed).shuffle(alternatives)
        choices = [correct, *alternatives[:3]]
        random.Random(seed + 1).shuffle(choices)
        return choices

    def add(question_id, prompt, category, difficulty, correct, pool, explanation, flag=None):
        options = options_for(correct, pool, int(hashlib.sha256(question_id.encode()).hexdigest()[:8], 16))
        record = {
            "id": question_id,
            "question": prompt,
            "category": category,
            "difficulty": difficulty,
            "options": options,
            "correct_answer": correct,
            "explanation": explanation,
            "media": {"type": "flag", "value": flag} if flag else None,
            "answer_type": "choice",
        }
        questions.append(record)

    for country in countries:
        name, capital, currency, continent, flag = (
            country["name"], country["capital"], country["currency"], country["continent"], country["flag"]
        )
        slug = hashlib.sha1(name.encode()).hexdigest()[:10]
        add(f"{slug}-capital", f"What is the capital of {name}?", "Capital cities", "easy",
            capital, all_capitals, f"{capital} is the capital of {name}.")
        add(f"{slug}-identify", f"Which country has {capital} as its capital?", "Country identification", "medium",
            name, all_names, f"{capital} is the capital of {name}.")
        add(f"{slug}-currency", f"Which currency is used in {name}?", "Currencies", "medium",
            currency, all_currencies, f"The currency listed for {name} is the {currency}.")
        add(f"{slug}-continent", f"On which continent is {name}?", "Continents", "easy",
            continent, all_continents, f"{name} is in {continent}.")
        add(f"{slug}-flag", "Which country does this flag represent?", "Flags", "easy",
            name, all_names, f"This is the flag of {name}.", flag)

    for index, (prompt, category, correct, other_options, answer, explanation) in enumerate(GEOGRAPHY):
        choices = [answer, *other_options]
        seed = int(hashlib.sha256(f"geo-{index}".encode()).hexdigest()[:8], 16)
        random.Random(seed).shuffle(choices)
        questions.append({
            "id": f"geo-{index + 1:03d}",
            "question": prompt,
            "category": category,
            "difficulty": "hard" if category == "World records" else "medium",
            "options": choices,
            "correct_answer": answer,
            "explanation": explanation,
            "media": None,
            "answer_type": "choice",
        })
    for index, (prompt, correct, other_options) in enumerate(LANGUAGES):
        answer_options = [correct, *other_options]
        random.Random(index + 401).shuffle(answer_options)
        questions.append({
            "id": f"language-{index + 1:03d}",
            "question": prompt,
            "category": "Languages",
            "difficulty": "medium",
            "options": answer_options,
            "correct_answer": correct,
            "explanation": f"{correct} is a language used officially in the country named in the question.",
            "media": None,
            "answer_type": "choice",
        })
    for index, (country, population, other_options) in enumerate(POPULATIONS_2023):
        answer_options = [population, *other_options]
        random.Random(index + 801).shuffle(answer_options)
        questions.append({
            "id": f"population-{index + 1:03d}",
            "question": f"About how large was the population of {country} in 2023?",
            "category": "Population",
            "difficulty": "medium",
            "options": answer_options,
            "correct_answer": population,
            "explanation": f"The World Bank's 2023 population estimate for {country} was {population}.",
            "media": None,
            "answer_type": "choice",
        })
    for index, (prompt, correct, other_options) in enumerate(BORDERS):
        answer_options = [correct, *other_options]
        random.Random(index + 1201).shuffle(answer_options)
        questions.append({
            "id": f"border-{index + 1:03d}",
            "question": prompt,
            "category": "Country borders",
            "difficulty": "hard",
            "options": answer_options,
            "correct_answer": correct,
            "explanation": f"{correct} shares a land border with the country in the question.",
            "media": None,
            "answer_type": "choice",
        })
    for index, (prompt, latitude, longitude, answer, other_options) in enumerate(MAP_QUESTIONS):
        answer_options = [answer, *other_options]
        random.Random(index + 1601).shuffle(answer_options)
        questions.append({
            "id": f"map-{index + 1:03d}",
            "question": prompt,
            "category": "Map reading",
            "difficulty": "medium",
            "options": answer_options,
            "correct_answer": answer,
            "explanation": f"The marked coordinates are {abs(latitude)}° {'N' if latitude >= 0 else 'S'}, "
                           f"{abs(longitude)}° {'E' if longitude >= 0 else 'W'}. {answer} is the correct location or region.",
            "media": {"type": "map", "value": {"latitude": latitude, "longitude": longitude}},
            "answer_type": "choice",
        })
    for index, (prompt, answer, tolerance, unit, answer_display, minimum, maximum, explanation) in enumerate(NUMERICAL_ESTIMATES):
        questions.append({
            "id": f"estimate-{index + 1:03d}",
            "question": prompt,
            "category": "Numerical estimation",
            "difficulty": "hard",
            "options": [],
            "correct_answer": answer,
            "correct_answer_display": answer_display,
            "tolerance": tolerance,
            "unit": unit,
            "min_value": minimum,
            "max_value": maximum,
            "explanation": explanation,
            "media": None,
            "answer_type": "number",
        })
    return questions


def daily_questions(date_string, question_bank, count=10):
    seed = int(hashlib.sha256(date_string.encode("ascii")).hexdigest(), 16)
    grouped = {}
    for question in question_bank:
        grouped.setdefault(question["category"], []).append(question)
    categories = sorted(grouped)
    generator = random.Random(seed)
    selected_categories = generator.sample(categories, min(count, len(categories)))
    questions = [
        generator.choice(sorted(grouped[category], key=lambda question: question["id"]))
        for category in selected_categories
    ]
    generator.shuffle(questions)
    return questions


def public_question(question):
    public = {
        key: question[key]
        for key in ("id", "question", "category", "difficulty", "options", "media", "answer_type")
    }
    if question["answer_type"] == "number":
        public.update({
            "unit": question["unit"],
            "min_value": question["min_value"],
            "max_value": question["max_value"],
        })
    return public


def serialize_question(question):
    return json.dumps(question, ensure_ascii=False, separators=(",", ":"))
