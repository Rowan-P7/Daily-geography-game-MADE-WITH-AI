import hashlib
import json
import random
import re
import unicodedata

from geogame.question_bank import COUNTRIES


GAME_TYPES = (
    {"id": "mystery_country", "name": "Mystery country", "verb": "Reveal clues, then name the country.", "mechanic": "guess"},
    {"id": "higher_lower", "name": "Higher or lower", "verb": "Compare two places across real-world stats.", "mechanic": "compare"},
    {"id": "country_outline", "name": "Country outline", "verb": "Read the shape. Type the country.", "mechanic": "outline"},
    {"id": "closest_wins", "name": "Closest wins", "verb": "Estimate the number. Closer earns more.", "mechanic": "estimate"},
    {"id": "flag_connections", "name": "Flag connections", "verb": "Tap every flag that fits the clue.", "mechanic": "multi_select"},
    {"id": "where_in_world", "name": "Where in the world?", "verb": "Study the landmark, then place it.", "mechanic": "photo_guess"},
    {"id": "border_battle", "name": "Border battle", "verb": "Tap the countries that share a land border.", "mechanic": "map_select"},
    {"id": "geography_connections", "name": "Geography connections", "verb": "Spot the thread between these places.", "mechanic": "connection"},
)

DIFFICULTIES = ("easy", "medium", "hard", "expert")

COUNTRY_FACTS = {
    "Algeria": {"population": 45_600_000, "area": 2_381_741, "borders": 7, "density": 19, "elevation": 800, "continent": "Africa", "neighbors": ["Tunisia", "Libya", "Niger", "Mali", "Mauritania", "Morocco", "Western Sahara"]},
    "Argentina": {"population": 45_800_000, "area": 2_780_400, "borders": 5, "density": 17, "elevation": 595, "continent": "South America", "neighbors": ["Chile", "Bolivia", "Paraguay", "Brazil", "Uruguay"]},
    "Australia": {"population": 26_600_000, "area": 7_692_024, "borders": 0, "density": 3, "elevation": 330, "continent": "Oceania", "neighbors": []},
    "Austria": {"population": 9_100_000, "area": 83_879, "borders": 8, "density": 109, "elevation": 910, "continent": "Europe", "neighbors": ["Germany", "Czechia", "Slovakia", "Hungary", "Slovenia", "Italy", "Switzerland", "Liechtenstein"]},
    "Belgium": {"population": 11_700_000, "area": 30_528, "borders": 4, "density": 383, "elevation": 181, "continent": "Europe", "neighbors": ["France", "Germany", "Luxembourg", "Netherlands"]},
    "Bhutan": {"population": 790_000, "area": 38_394, "borders": 2, "density": 21, "elevation": 2220, "continent": "Asia", "neighbors": ["China", "India"]},
    "Brazil": {"population": 203_100_000, "area": 8_515_767, "borders": 10, "density": 24, "elevation": 320, "continent": "South America", "neighbors": ["Argentina", "Bolivia", "Colombia", "Guyana", "Paraguay", "Peru", "Suriname", "Uruguay", "Venezuela", "France"]},
    "Canada": {"population": 40_100_000, "area": 9_984_670, "borders": 1, "density": 4, "elevation": 487, "continent": "North America", "neighbors": ["United States"]},
    "Chile": {"population": 19_600_000, "area": 756_102, "borders": 3, "density": 26, "elevation": 1871, "continent": "South America", "neighbors": ["Argentina", "Bolivia", "Peru"]},
    "China": {"population": 1_410_700_000, "area": 9_596_961, "borders": 14, "density": 147, "elevation": 1840, "continent": "Asia", "neighbors": ["Afghanistan", "Bhutan", "India", "Kazakhstan", "Kyrgyzstan", "Laos", "Mongolia", "Myanmar", "Nepal", "North Korea", "Pakistan", "Russia", "Tajikistan", "Vietnam"]},
    "Colombia": {"population": 52_100_000, "area": 1_141_748, "borders": 5, "density": 46, "elevation": 593, "continent": "South America", "neighbors": ["Brazil", "Ecuador", "Panama", "Peru", "Venezuela"]},
    "Costa Rica": {"population": 5_200_000, "area": 51_100, "borders": 2, "density": 102, "elevation": 746, "continent": "North America", "neighbors": ["Nicaragua", "Panama"]},
    "Croatia": {"population": 3_900_000, "area": 56_594, "borders": 5, "density": 69, "elevation": 331, "continent": "Europe", "neighbors": ["Slovenia", "Hungary", "Serbia", "Bosnia and Herzegovina", "Montenegro"]},
    "Czechia": {"population": 10_900_000, "area": 78_871, "borders": 4, "density": 138, "elevation": 433, "continent": "Europe", "neighbors": ["Germany", "Poland", "Slovakia", "Austria"]},
    "Denmark": {"population": 5_900_000, "area": 42_933, "borders": 1, "density": 138, "elevation": 34, "continent": "Europe", "neighbors": ["Germany"]},
    "Egypt": {"population": 112_700_000, "area": 1_001_450, "borders": 4, "density": 113, "elevation": 321, "continent": "Africa", "neighbors": ["Libya", "Sudan", "Israel", "Palestine"]},
    "Ethiopia": {"population": 126_500_000, "area": 1_104_300, "borders": 6, "density": 115, "elevation": 1330, "continent": "Africa", "neighbors": ["Eritrea", "Djibouti", "Somalia", "Kenya", "South Sudan", "Sudan"]},
    "Finland": {"population": 5_600_000, "area": 338_455, "borders": 3, "density": 18, "elevation": 164, "continent": "Europe", "neighbors": ["Sweden", "Norway", "Russia"]},
    "France": {"population": 68_200_000, "area": 643_801, "borders": 8, "density": 106, "elevation": 375, "continent": "Europe", "neighbors": ["Belgium", "Luxembourg", "Germany", "Switzerland", "Italy", "Monaco", "Spain", "Andorra"]},
    "Germany": {"population": 84_500_000, "area": 357_588, "borders": 9, "density": 236, "elevation": 263, "continent": "Europe", "neighbors": ["Denmark", "Poland", "Czechia", "Austria", "Switzerland", "France", "Luxembourg", "Belgium", "Netherlands"]},
    "Ghana": {"population": 34_100_000, "area": 238_533, "borders": 3, "density": 143, "elevation": 190, "continent": "Africa", "neighbors": ["Côte d'Ivoire", "Burkina Faso", "Togo"]},
    "Greece": {"population": 10_400_000, "area": 131_957, "borders": 4, "density": 79, "elevation": 498, "continent": "Europe", "neighbors": ["Albania", "North Macedonia", "Bulgaria", "Turkey"]},
    "Iceland": {"population": 390_000, "area": 103_000, "borders": 0, "density": 4, "elevation": 557, "continent": "Europe", "neighbors": []},
    "India": {"population": 1_438_100_000, "area": 3_287_263, "borders": 6, "density": 481, "elevation": 621, "continent": "Asia", "neighbors": ["Pakistan", "China", "Nepal", "Bhutan", "Bangladesh", "Myanmar"]},
    "Indonesia": {"population": 277_500_000, "area": 1_904_569, "borders": 3, "density": 146, "elevation": 367, "continent": "Asia", "neighbors": ["Malaysia", "Papua New Guinea", "Timor-Leste"]},
    "Iran": {"population": 89_200_000, "area": 1_648_195, "borders": 7, "density": 54, "elevation": 1305, "continent": "Asia", "neighbors": ["Armenia", "Azerbaijan", "Turkmenistan", "Afghanistan", "Pakistan", "Iraq", "Turkey"]},
    "Ireland": {"population": 5_300_000, "area": 70_273, "borders": 1, "density": 75, "elevation": 118, "continent": "Europe", "neighbors": ["United Kingdom"]},
    "Italy": {"population": 58_900_000, "area": 301_340, "borders": 6, "density": 195, "elevation": 538, "continent": "Europe", "neighbors": ["France", "Switzerland", "Austria", "Slovenia", "San Marino", "Vatican City"]},
    "Japan": {"population": 124_500_000, "area": 377_975, "borders": 0, "density": 338, "elevation": 438, "continent": "Asia", "neighbors": []},
    "Kenya": {"population": 55_100_000, "area": 580_367, "borders": 5, "density": 95, "elevation": 762, "continent": "Africa", "neighbors": ["Ethiopia", "Somalia", "Tanzania", "Uganda", "South Sudan"]},
    "Lesotho": {"population": 2_300_000, "area": 30_355, "borders": 1, "density": 76, "elevation": 2161, "continent": "Africa", "neighbors": ["South Africa"]},
    "Madagascar": {"population": 30_300_000, "area": 587_041, "borders": 0, "density": 52, "elevation": 615, "continent": "Africa", "neighbors": []},
    "Mexico": {"population": 129_700_000, "area": 1_964_375, "borders": 3, "density": 66, "elevation": 1111, "continent": "North America", "neighbors": ["United States", "Guatemala", "Belize"]},
    "Nepal": {"population": 29_700_000, "area": 147_516, "borders": 2, "density": 201, "elevation": 3265, "continent": "Asia", "neighbors": ["China", "India"]},
    "Netherlands": {"population": 17_900_000, "area": 41_543, "borders": 2, "density": 431, "elevation": 30, "continent": "Europe", "neighbors": ["Belgium", "Germany"]},
    "New Zealand": {"population": 5_200_000, "area": 268_021, "borders": 0, "density": 20, "elevation": 388, "continent": "Oceania", "neighbors": []},
    "Nigeria": {"population": 223_800_000, "area": 923_768, "borders": 4, "density": 242, "elevation": 380, "continent": "Africa", "neighbors": ["Benin", "Niger", "Chad", "Cameroon"]},
    "Norway": {"population": 5_500_000, "area": 385_207, "borders": 3, "density": 15, "elevation": 460, "continent": "Europe", "neighbors": ["Sweden", "Finland", "Russia"]},
    "Pakistan": {"population": 240_500_000, "area": 881_913, "borders": 4, "density": 287, "elevation": 900, "continent": "Asia", "neighbors": ["India", "Afghanistan", "Iran", "China"]},
    "Peru": {"population": 34_400_000, "area": 1_285_216, "borders": 5, "density": 27, "elevation": 1555, "continent": "South America", "neighbors": ["Ecuador", "Colombia", "Brazil", "Bolivia", "Chile"]},
    "Philippines": {"population": 117_300_000, "area": 300_000, "borders": 0, "density": 393, "elevation": 442, "continent": "Asia", "neighbors": []},
    "Poland": {"population": 36_700_000, "area": 312_696, "borders": 7, "density": 117, "elevation": 173, "continent": "Europe", "neighbors": ["Germany", "Czechia", "Slovakia", "Ukraine", "Belarus", "Lithuania", "Russia"]},
    "Portugal": {"population": 10_500_000, "area": 92_212, "borders": 1, "density": 114, "elevation": 372, "continent": "Europe", "neighbors": ["Spain"]},
    "Romania": {"population": 19_100_000, "area": 238_397, "borders": 5, "density": 80, "elevation": 414, "continent": "Europe", "neighbors": ["Ukraine", "Moldova", "Bulgaria", "Serbia", "Hungary"]},
    "Russia": {"population": 144_400_000, "area": 17_098_246, "borders": 14, "density": 9, "elevation": 600, "continent": "Europe and Asia", "neighbors": ["Norway", "Finland", "Estonia", "Latvia", "Lithuania", "Poland", "Belarus", "Ukraine", "Georgia", "Azerbaijan", "Kazakhstan", "China", "Mongolia", "North Korea"]},
    "Rwanda": {"population": 14_100_000, "area": 26_338, "borders": 4, "density": 535, "elevation": 1598, "continent": "Africa", "neighbors": ["Uganda", "Tanzania", "Burundi", "Democratic Republic of the Congo"]},
    "Saudi Arabia": {"population": 36_900_000, "area": 2_149_690, "borders": 7, "density": 17, "elevation": 665, "continent": "Asia", "neighbors": ["Jordan", "Iraq", "Kuwait", "Qatar", "United Arab Emirates", "Oman", "Yemen"]},
    "Senegal": {"population": 18_100_000, "area": 196_722, "borders": 5, "density": 92, "elevation": 69, "continent": "Africa", "neighbors": ["Mauritania", "Mali", "Guinea", "Guinea-Bissau", "The Gambia"]},
    "Singapore": {"population": 5_900_000, "area": 734, "borders": 0, "density": 8030, "elevation": 15, "continent": "Asia", "neighbors": []},
    "South Africa": {"population": 62_000_000, "area": 1_221_037, "borders": 6, "density": 51, "elevation": 1034, "continent": "Africa", "neighbors": ["Namibia", "Botswana", "Zimbabwe", "Mozambique", "Eswatini", "Lesotho"]},
    "South Korea": {"population": 51_700_000, "area": 100_210, "borders": 1, "density": 515, "elevation": 282, "continent": "Asia", "neighbors": ["North Korea"]},
    "Spain": {"population": 48_400_000, "area": 505_990, "borders": 5, "density": 96, "elevation": 660, "continent": "Europe", "neighbors": ["Portugal", "France", "Andorra", "Gibraltar", "Morocco"]},
    "Sweden": {"population": 10_500_000, "area": 450_295, "borders": 2, "density": 25, "elevation": 320, "continent": "Europe", "neighbors": ["Norway", "Finland"]},
    "Switzerland": {"population": 8_900_000, "area": 41_285, "borders": 5, "density": 216, "elevation": 1350, "continent": "Europe", "neighbors": ["Germany", "France", "Italy", "Austria", "Liechtenstein"]},
    "Thailand": {"population": 71_800_000, "area": 513_120, "borders": 4, "density": 140, "elevation": 287, "continent": "Asia", "neighbors": ["Myanmar", "Laos", "Cambodia", "Malaysia"]},
    "Turkey": {"population": 85_300_000, "area": 783_562, "borders": 8, "density": 109, "elevation": 1132, "continent": "Europe and Asia", "neighbors": ["Greece", "Bulgaria", "Georgia", "Armenia", "Azerbaijan", "Iran", "Iraq", "Syria"]},
    "Uganda": {"population": 48_600_000, "area": 241_550, "borders": 5, "density": 201, "elevation": 1100, "continent": "Africa", "neighbors": ["South Sudan", "Kenya", "Tanzania", "Rwanda", "Democratic Republic of the Congo"]},
    "Ukraine": {"population": 37_000_000, "area": 603_550, "borders": 7, "density": 61, "elevation": 175, "continent": "Europe", "neighbors": ["Belarus", "Russia", "Poland", "Slovakia", "Hungary", "Romania", "Moldova"]},
    "United Kingdom": {"population": 68_700_000, "area": 243_610, "borders": 1, "density": 282, "elevation": 162, "continent": "Europe", "neighbors": ["Ireland"]},
    "United States": {"population": 334_900_000, "area": 9_833_517, "borders": 2, "density": 36, "elevation": 760, "continent": "North America", "neighbors": ["Canada", "Mexico"]},
    "Vietnam": {"population": 100_300_000, "area": 331_212, "borders": 3, "density": 303, "elevation": 398, "continent": "Asia", "neighbors": ["China", "Laos", "Cambodia"]},
    "Zambia": {"population": 20_600_000, "area": 752_612, "borders": 8, "density": 27, "elevation": 1138, "continent": "Africa", "neighbors": ["Democratic Republic of the Congo", "Tanzania", "Malawi", "Mozambique", "Zimbabwe", "Botswana", "Namibia", "Angola"]},
    "Zimbabwe": {"population": 16_300_000, "area": 390_757, "borders": 4, "density": 42, "elevation": 1142, "continent": "Africa", "neighbors": ["Zambia", "Mozambique", "South Africa", "Botswana"]},
}

FLAG_EMOJI = {
    "Algeria": "🇩🇿", "Pakistan": "🇵🇰", "Turkey": "🇹🇷", "Tunisia": "🇹🇳",
    "Malaysia": "🇲🇾", "Singapore": "🇸🇬", "Japan": "🇯🇵", "Canada": "🇨🇦",
    "Austria": "🇦🇹", "Bhutan": "🇧🇹", "Bolivia": "🇧🇴", "Nepal": "🇳🇵",
    "Paraguay": "🇵🇾", "Switzerland": "🇨🇭", "Peru": "🇵🇪", "Chile": "🇨🇱",
    "Argentina": "🇦🇷", "Colombia": "🇨🇴", "Ecuador": "🇪🇨", "Uruguay": "🇺🇾",
    "Portugal": "🇵🇹", "Spain": "🇪🇸", "Bangladesh": "🇧🇩", "Laos": "🇱🇦",
    "Palau": "🇵🇼", "South Korea": "🇰🇷", "Vietnam": "🇻🇳", "Thailand": "🇹🇭",
    "Australia": "🇦🇺", "Fiji": "🇫🇯", "New Zealand": "🇳🇿", "Samoa": "🇼🇸",
    "Solomon Islands": "🇸🇧", "Tonga": "🇹🇴", "Vanuatu": "🇻🇺", "Madagascar": "🇲🇬",
    "Lebanon": "🇱🇧", "Cyprus": "🇨🇾", "Jordan": "🇯🇴", "Syria": "🇸🇾",
    "Egypt": "🇪🇬", "Iraq": "🇮🇶", "Ghana": "🇬🇭", "Kenya": "🇰🇪",
    "Morocco": "🇲🇦", "Senegal": "🇸🇳", "India": "🇮🇳", "Germany": "🇩🇪",
    "France": "🇫🇷", "Luxembourg": "🇱🇺", "Netherlands": "🇳🇱",
    "Poland": "🇵🇱", "Denmark": "🇩🇰", "Czechia": "🇨🇿",
    "Zambia": "🇿🇲", "Monaco": "🇲🇨", "Lesotho": "🇱🇸",
}

OUTLINE_NAMES = {
    "easy": ["Australia", "Italy", "Japan", "Madagascar", "New Zealand", "South Africa"],
    "medium": ["Chile", "Greece", "Norway", "Portugal", "Vietnam", "Thailand"],
    "hard": ["Bhutan", "Croatia", "Denmark", "Lesotho", "Rwanda", "Singapore"],
    "expert": ["Eswatini", "Luxembourg", "Montenegro", "Slovenia", "The Gambia", "Brunei"],
}

OUTLINE_GEO_NAMES = {
    "United States": "United States of America",
    "Tanzania": "United Republic of Tanzania",
    "Serbia": "Republic of Serbia",
    "The Gambia": "Gambia",
    "Eswatini": "eSwatini",
    "Côte d'Ivoire": "Ivory Coast",
}

LANDMARKS = [
    {"name": "Machu Picchu", "country": "Peru", "place": "Cusco Region", "clue": "High in the Andes, above the Urubamba River valley.", "file": "Machu_Picchu%2C_Peru.jpg", "credit": "Pedro Szekely · CC BY-SA 2.0", "source": "https://commons.wikimedia.org/wiki/File:Machu_Picchu,_Peru.jpg"},
    {"name": "Eiffel Tower", "country": "France", "place": "Paris", "clue": "Look for the Seine and the capital of a western European country.", "file": "Eiffel_Tower%2C_Paris.jpg", "credit": "Kate · CC BY-SA 3.0", "source": "https://commons.wikimedia.org/wiki/File:Eiffel_Tower,_Paris.jpg"},
    {"name": "Taj Mahal", "country": "India", "place": "Agra", "clue": "This marble mausoleum stands near the Yamuna River.", "file": "Taj_Mahal%2C_Agra%2C_India.jpg", "credit": "Yann · CC BY-SA 4.0", "source": "https://commons.wikimedia.org/wiki/File:Taj_Mahal,_Agra,_India.jpg"},
    {"name": "Petra", "country": "Jordan", "place": "Ma'an Governorate", "clue": "An ancient Nabataean city carved into rose-coloured rock.", "file": "The_Monastery%2C_Petra%2C_Jordan.jpg", "credit": "Charlie Phillips · CC BY 2.0", "source": "https://commons.wikimedia.org/wiki/File:The_Monastery,_Petra,_Jordan.jpg"},
    {"name": "Sydney Opera House", "country": "Australia", "place": "Sydney", "clue": "Sails look out over Port Jackson in the Southern Hemisphere.", "file": "Sydney_Opera_House_-_Dec_2008.jpg", "credit": "Diliff · CC BY-SA 3.0", "source": "https://commons.wikimedia.org/wiki/File:Sydney_Opera_House_-_Dec_2008.jpg"},
    {"name": "Mount Kilimanjaro", "country": "Tanzania", "place": "Kilimanjaro Region", "clue": "A snow-capped volcanic massif rises above East African plains.", "file": "Mount_Kilimanjaro.jpg", "credit": "Muhammad Mahdi Karim · GFDL 1.2", "source": "https://commons.wikimedia.org/wiki/File:Mount_Kilimanjaro.jpg"},
    {"name": "Golden Gate Bridge", "country": "United States", "place": "San Francisco", "clue": "A suspension bridge spans the strait at a Pacific coast city.", "file": "Golden_Gate_Bridge_as_seen_from_Battery_East.jpg", "credit": "Frank Schulenburg · CC BY-SA 4.0", "source": "https://commons.wikimedia.org/wiki/File:Golden_Gate_Bridge_as_seen_from_Battery_East.jpg"},
    {"name": "Christ the Redeemer", "country": "Brazil", "place": "Rio de Janeiro", "clue": "A hilltop statue overlooks Guanabara Bay and Sugarloaf Mountain.", "file": "Cristo_Redentor_-_Rio_de_Janeiro%2C_Brasil.jpg", "credit": "Nico Kaiser · CC BY 2.0", "source": "https://commons.wikimedia.org/wiki/File:Cristo_Redentor_-_Rio_de_Janeiro,_Brasil.jpg"},
    {"name": "Angkor Wat", "country": "Cambodia", "place": "Siem Reap", "clue": "A vast temple complex sits in mainland Southeast Asia.", "file": "Angkor_Wat.jpg", "credit": "Bj\u00f6rn Christian T\u00f6rrissen · CC BY-SA 4.0", "source": "https://commons.wikimedia.org/wiki/File:Angkor_Wat.jpg"},
    {"name": "Acropolis of Athens", "country": "Greece", "place": "Athens", "clue": "An ancient hilltop citadel stands above a Mediterranean capital.", "file": "Acropolis_Parthenon_Athens_Greece.jpg", "credit": "Jebulon · CC0", "source": "https://commons.wikimedia.org/wiki/File:Acropolis_Parthenon_Athens_Greece.jpg"},
    {"name": "Mount Fuji", "country": "Japan", "place": "Honshu", "clue": "A near-symmetrical volcano stands west of Tokyo.", "file": "Mount_Fuji_from Lake_Kawaguchi.jpg", "credit": "Subramaniam K V · CC BY 3.0", "source": "https://commons.wikimedia.org/wiki/File:Mount_Fuji_from_Lake_Kawaguchi.jpg"},
    {"name": "Pyramids of Giza", "country": "Egypt", "place": "Giza", "clue": "Ancient monuments rise on the edge of the Nile Valley.", "file": "All_Gizah_Pyramids.jpg", "credit": "Ricardo Liberato · CC BY-SA 2.0", "source": "https://commons.wikimedia.org/wiki/File:All_Gizah_Pyramids.jpg"},
]

FLAG_SETS = [
    {"clue": "Select every flag with a crescent moon.", "countries": ["Algeria", "Pakistan", "Turkey", "Tunisia", "Malaysia", "Singapore", "Japan", "Canada"], "correct": ["Algeria", "Pakistan", "Turkey", "Tunisia", "Malaysia", "Singapore"], "difficulty": "medium"},
    {"clue": "Select every landlocked country.", "countries": ["Austria", "Bhutan", "Bolivia", "Nepal", "Paraguay", "Switzerland", "Peru", "Chile"], "correct": ["Austria", "Bhutan", "Bolivia", "Nepal", "Paraguay", "Switzerland"], "difficulty": "hard"},
    {"clue": "Select every country in South America.", "countries": ["Argentina", "Chile", "Colombia", "Ecuador", "Peru", "Uruguay", "Portugal", "Spain"], "correct": ["Argentina", "Chile", "Colombia", "Ecuador", "Peru", "Uruguay"], "difficulty": "easy"},
    {"clue": "Select every country that borders Germany.", "countries": ["Austria", "Belgium", "Czechia", "Denmark", "France", "Luxembourg", "Netherlands", "Poland", "Switzerland", "Spain"], "correct": ["Austria", "Belgium", "Czechia", "Denmark", "France", "Luxembourg", "Netherlands", "Poland", "Switzerland"], "difficulty": "expert"},
    {"clue": "Select every flag with a prominent red circle or disc.", "countries": ["Bangladesh", "Japan", "Laos", "Palau", "South Korea", "Vietnam", "Singapore", "Canada"], "correct": ["Bangladesh", "Japan", "Laos"], "difficulty": "hard"},
    {"clue": "Select every country in Africa.", "countries": ["Algeria", "Ghana", "Kenya", "Morocco", "Senegal", "Tunisia", "India", "Jordan"], "correct": ["Algeria", "Ghana", "Kenya", "Morocco", "Senegal", "Tunisia"], "difficulty": "easy"},
    {"clue": "Select every country whose flag includes a cedar tree.", "countries": ["Lebanon", "Cyprus", "Jordan", "Syria", "Egypt", "Iraq"], "correct": ["Lebanon"], "difficulty": "expert"},
    {"clue": "Select every country in Oceania.", "countries": ["Australia", "Fiji", "New Zealand", "Samoa", "Solomon Islands", "Tonga", "Vanuatu", "Madagascar"], "correct": ["Australia", "Fiji", "New Zealand", "Samoa", "Solomon Islands", "Tonga", "Vanuatu"], "difficulty": "medium"},
]

CONNECTIONS = [
    {"prompt": "What connects these countries?", "items": ["Austria", "Germany", "Hungary", "Slovakia"], "answer": "Every one touches the Danube.", "accepted": ["Danube", "danube river", "Danube River"], "fact": "The Danube flows through or along all four countries."},
    {"prompt": "What connects these countries?", "items": ["Bolivia", "Paraguay", "Switzerland", "Austria"], "answer": "They are all landlocked.", "accepted": ["landlocked", "no coastline", "land locked"], "fact": "None of these countries has a coastline."},
    {"prompt": "What connects these countries?", "items": ["Ecuador", "El Salvador", "Panama", "Timor-Leste"], "answer": "They use the United States dollar as legal tender.", "accepted": ["us dollar", "united states dollar", "dollar"], "fact": "Each uses the US dollar as its official currency."},
    {"prompt": "What connects these countries?", "items": ["Lesotho", "San Marino", "Vatican City", "South Africa"], "answer": "The first three are enclaves within another country.", "accepted": ["enclave", "enclaves"], "fact": "Lesotho is enclosed by South Africa; San Marino and Vatican City are enclosed by Italy."},
    {"prompt": "What connects these countries?", "items": ["Gambia", "Senegal", "Portugal", "Spain"], "answer": "Each pair shares a border; one country is almost surrounded by the other.", "accepted": ["shared border", "border", "almost surrounded"], "fact": "The Gambia is nearly enclosed by Senegal; Portugal is bordered by Spain."},
    {"prompt": "What connects these countries?", "items": ["Kazakhstan", "Mongolia", "Nepal", "Bhutan"], "answer": "They are all in Asia and have no coastline.", "accepted": ["landlocked", "no coastline", "land locked"], "fact": "All four are landlocked Asian countries."},
]

HIGHER_LOWER_PAIRS = [
    ("population", "Population", "people", "2023 World Bank estimates", [
        ("Argentina", 45_800_000, "Spain", 48_400_000, "easy"),
        ("Ghana", 34_100_000, "Senegal", 18_100_000, "easy"),
        ("Japan", 124_500_000, "Ethiopia", 126_500_000, "hard"),
        ("Vietnam", 100_300_000, "Philippines", 117_300_000, "medium"),
        ("France", 68_200_000, "United Kingdom", 68_700_000, "expert"),
        ("Australia", 26_600_000, "Madagascar", 30_300_000, "medium"),
        ("Canada", 40_100_000, "Poland", 36_700_000, "medium"),
        ("South Korea", 51_700_000, "Spain", 48_400_000, "hard"),
    ]),
    ("area", "Land area", "km²", "World Bank / national geographic area, reference varies by source", [
        ("Australia", 7_692_024, "India", 3_287_263, "easy"),
        ("Argentina", 2_780_400, "Algeria", 2_381_741, "medium"),
        ("Japan", 377_975, "Germany", 357_588, "hard"),
        ("Ghana", 238_533, "Uganda", 241_550, "expert"),
        ("Portugal", 92_212, "Austria", 83_879, "medium"),
        ("Nepal", 147_516, "Greece", 131_957, "hard"),
    ]),
    ("borders", "Land neighbours", "countries", "Curated international land-border counts", [
        ("France", 8, "Germany", 9, "medium"),
        ("Brazil", 10, "China", 14, "easy"),
        ("Peru", 5, "Colombia", 5, "expert"),
        ("Austria", 8, "Zambia", 8, "hard"),
        ("Ghana", 3, "Thailand", 4, "medium"),
        ("Romania", 5, "Ukraine", 7, "hard"),
    ]),
    ("density", "Population density", "people per km²", "2023 population divided by land area; rounded", [
        ("Netherlands", 431, "Belgium", 383, "medium"),
        ("Japan", 338, "Germany", 236, "hard"),
        ("India", 481, "Belgium", 383, "medium"),
        ("Singapore", 8030, "Monaco", 18800, "expert"),
    ]),
    ("elevation", "Mean elevation", "m above sea level", "CIA World Factbook geographic reference", [
        ("Bhutan", 2220, "Nepal", 3265, "expert"),
        ("Lesotho", 2161, "Switzerland", 1350, "medium"),
        ("Bolivia", 1192, "Ethiopia", 1330, "hard"),
        ("Netherlands", 30, "Denmark", 34, "expert"),
    ]),
    ("gdp", "GDP", "current US$", "World Bank indicator NY.GDP.MKTP.CD, 2023, rounded", [
        ("Germany", 4_560_000_000_000, "Japan", 4_210_000_000_000, "medium"),
        ("India", 3_570_000_000_000, "United Kingdom", 3_380_000_000_000, "hard"),
        ("Brazil", 2_170_000_000_000, "France", 3_050_000_000_000, "easy"),
        ("Indonesia", 1_370_000_000_000, "Mexico", 1_790_000_000_000, "hard"),
    ]),
]


def _seed(value):
    return int(hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16], 16)


def _slug(value):
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")


def _country(name):
    row = next((row for row in COUNTRIES if row[0] == name), None)
    if row is None:
        raise ValueError(f"Unknown country in challenge registry: {name}")
    return {"name": row[0], "capital": row[1], "currency": row[2], "continent": row[3], "flag": row[4]}


def _challenge(game_type, difficulty, content_id, payload, answer, explanation, source):
    return {
        "id": f"{game_type}-{difficulty}-{content_id}",
        "game_type": game_type,
        "difficulty": difficulty,
        "prompt": payload["prompt"],
        "payload": payload,
        "correct_answer": answer,
        "accepted_answers": payload.get("accepted_answers", []),
        "hints": payload.get("hints", []),
        "explanation": explanation,
        "source": source,
        "scoring": {"max_points": 1000},
    }


def _build_challenges():
    challenges = []
    outline_difficulty = {
        "Australia": "easy", "Italy": "easy", "Japan": "easy", "Madagascar": "easy",
        "New Zealand": "easy", "South Africa": "easy", "Chile": "medium", "Greece": "medium",
        "Norway": "medium", "Portugal": "medium", "Vietnam": "medium", "Thailand": "medium",
        "Bhutan": "hard", "Croatia": "hard", "Denmark": "hard", "Lesotho": "hard",
        "Rwanda": "hard", "Singapore": "hard", "Eswatini": "expert", "Luxembourg": "expert",
        "Montenegro": "expert", "Slovenia": "expert", "The Gambia": "expert", "Brunei": "expert",
    }
    for country, difficulty in outline_difficulty.items():
        geo_name = OUTLINE_GEO_NAMES.get(country, country)
        challenges.append(_challenge(
            "country_outline", difficulty, hashlib.sha256(country.encode()).hexdigest()[:12],
            {"prompt": "Name the country from its outline.", "country": country, "geo_name": geo_name,
             "aliases": [country, geo_name], "source": "Natural Earth 1:50m Admin 0 Countries"},
            country, f"The outline is {country}.", {"name": "Natural Earth", "url": "https://www.naturalearthdata.com/downloads/50m-cultural-vectors/50m-admin-0-countries/"},
        ))

    mystery_pool = [
        ("Japan", "expert", ["This island country is in East Asia.", "It has four main islands.", "Its highest mountain is a volcano.", "Its capital sits on Honshu.", "Its flag is a red disc on white."]),
        ("Australia", "easy", ["This country is also a continent.", "It lies in the Southern Hemisphere.", "Its capital is Canberra.", "Its flag includes the Union Jack.", "It has no land borders."]),
        ("Brazil", "easy", ["This is the largest country in South America by area.", "It faces the Atlantic Ocean.", "Its capital is Brasília.", "Portuguese is its official language.", "The Amazon Basin covers much of its north."]),
        ("Lesotho", "expert", ["This country is entirely surrounded by one neighbour.", "It is in southern Africa.", "All of its territory lies above 1,000 metres.", "Its capital is Maseru.", "Its neighbour is South Africa."]),
        ("Portugal", "medium", ["This European country faces the Atlantic.", "It shares a land border with one country.", "Its capital is Lisbon.", "The Tagus flows through its capital.", "Its only land neighbour is Spain."]),
        ("Bhutan", "hard", ["This Himalayan country is landlocked.", "It lies between two populous Asian states.", "Its capital is Thimphu.", "The national flag features a dragon.", "Its neighbours are China and India."]),
        ("Madagascar", "medium", ["This island country lies off Africa's southeast coast.", "The Mozambique Channel separates it from the mainland.", "Its capital is Antananarivo.", "Its flag has white, red and green.", "It is the world's second-largest island country by area."]),
        ("Senegal", "hard", ["This country is in western Africa.", "It nearly surrounds a much smaller neighbour.", "Its capital is Dakar.", "The Senegal River forms part of its northern border.", "Its neighbour is The Gambia."]),
        ("Nepal", "medium", ["This country is landlocked in South Asia.", "It lies along the Himalayas.", "Its capital is Kathmandu.", "Its flag is the only non-rectangular national flag.", "It is home to Mount Everest."]),
        ("Croatia", "hard", ["This country borders the Adriatic Sea.", "It is in southeastern Europe.", "Its capital is Zagreb.", "Its coastline includes many islands.", "Its flag has a red-and-white checkerboard shield."]),
    ]
    for country, difficulty, clues in mystery_pool:
        challenges.append(_challenge(
            "mystery_country", difficulty, hashlib.sha256(country.encode()).hexdigest()[:12],
            {"prompt": "Who is the mystery country?", "country": country, "clues": clues[:5],
             "initial_clues": 1, "accepted_answers": [country]},
            country, f"The country was {country}. " + clues[-1],
            {"name": "CIA World Factbook", "url": "https://www.cia.gov/the-world-factbook/"},
        ))

    for metric, label, unit, reference, pairs in HIGHER_LOWER_PAIRS:
        for index, (left, left_value, right, right_value, difficulty) in enumerate(pairs):
            challenges.append(_challenge(
                "higher_lower", difficulty, f"{metric}-{index + 1}",
                {"prompt": f"Which country has the higher {label.lower()}?", "left": left, "right": right,
                 "metric": metric, "metric_label": label, "unit": unit, "reference": reference,
                 "left_flag": FLAG_EMOJI.get(left) or _country(left)["flag"],
                 "right_flag": FLAG_EMOJI.get(right) or _country(right)["flag"],
                 "left_value": left_value, "right_value": right_value},
                "left" if left_value > right_value else "right" if right_value > left_value else "tie",
                f"{left}: {left_value:,} {unit}. {right}: {right_value:,} {unit}. Source reference: {reference}.",
                {"name": "World Bank / curated border counts", "reference_year": "2023 where stated"},
            ))

    landmark_difficulties = {
        "Machu Picchu": "hard", "Eiffel Tower": "easy", "Taj Mahal": "medium",
        "Petra": "hard", "Sydney Opera House": "easy", "Mount Kilimanjaro": "expert",
        "Golden Gate Bridge": "medium", "Christ the Redeemer": "medium",
        "Angkor Wat": "hard", "Acropolis of Athens": "medium", "Mount Fuji": "expert",
        "Pyramids of Giza": "easy",
    }
    for landmark in LANDMARKS:
        country = landmark["country"]
        difficulty = landmark_difficulties[landmark["name"]]
        if landmark["name"] == "Mount Kilimanjaro":
            expected, prompt = "Kilimanjaro Region", "Which Tanzanian region contains this mountain?"
            accepted = [expected]
        elif landmark["name"] == "Mount Fuji":
            expected, prompt = "Honshu", "Which main Japanese island is home to this mountain?"
            accepted = [expected]
        elif difficulty == "easy":
            expected, prompt = country, "Which country is this landmark in?"
            accepted = [country]
        elif difficulty == "medium":
            expected, prompt = landmark["place"], "Which city or region is this landmark in?"
            accepted = [expected]
        else:
            expected, prompt = landmark["name"], "Name this geographical landmark."
            accepted = [expected]
        challenges.append(_challenge(
            "where_in_world", difficulty, hashlib.sha256(landmark["name"].encode()).hexdigest()[:12],
            {"prompt": prompt, "landmark": landmark["name"],
             "region": landmark["place"], "country": country,
             "photo_url": f"/static/photos/{hashlib.sha256(landmark['name'].encode()).hexdigest()[:12]}.jpg",
             "photo_source": landmark["source"], "photo_credit": landmark["credit"],
             "hints": [landmark["clue"], f"It is in {COUNTRY_FACTS.get(country, {}).get('continent', 'the world')}."],
             "accepted_answers": accepted},
            expected, f"{landmark['name']} is in {landmark['place']}, {country}.",
            {"name": "Wikimedia Commons", "url": landmark["source"]},
        ))

    for index, flag_set in enumerate(FLAG_SETS):
        countries = [
            {"name": name, "flag": FLAG_EMOJI.get(name) or _country(name)["flag"]}
            for name in flag_set["countries"]
        ]
        challenges.append(_challenge(
            "flag_connections", flag_set["difficulty"], f"flags-{index + 1}",
            {"prompt": flag_set["clue"], "flags": countries, "timer_seconds": 30 + index * 5},
            sorted(flag_set["correct"]), f"{', '.join(flag_set['correct'])} fit the connection.",
            {"name": "Unicode CLDR country flag sequences", "url": "https://www.unicode.org/emoji/charts/full-emoji-list.html"},
        ))

    for index, (prompt, items, answer, accepted, fact) in enumerate(CONNECTIONS):
        challenges.append(_challenge(
            "geography_connections", ("easy", "medium", "hard", "expert")[index % 4], f"connection-{index + 1}",
            {"prompt": prompt, "items": items, "answer_placeholder": "Type the connection in a few words.",
             "accepted_answers": accepted},
            answer, fact, {"name": "CIA World Factbook / reference geography", "url": "https://www.cia.gov/the-world-factbook/"},
        ))

    # Border Battle uses the selected country and a mixture of true neighbours
    # and nearby distractors; all geometries are served from Natural Earth.
    border_examples = [
        ("Germany", "medium"), ("Brazil", "hard"), ("Nepal", "medium"),
        ("Senegal", "hard"), ("Austria", "hard"), ("Kenya", "hard"),
        ("Vietnam", "medium"), ("Croatia", "medium"), ("Canada", "easy"),
        ("Lesotho", "easy"), ("France", "expert"), ("Zambia", "expert"),
    ]
    for index, (country, difficulty) in enumerate(border_examples):
        neighbors = COUNTRY_FACTS[country]["neighbors"]
        displayable = list(neighbors)
        distractors = [
            name for name in ("France", "Poland", "Italy", "Spain", "Kenya", "Japan", "China", "India", "Ghana", "Peru", "Thailand", "Zambia")
            if name != country and name not in displayable
        ]
        rng = random.Random(_seed(country))
        rng.shuffle(distractors)
        options = sorted(set(displayable + distractors[:max(5, 9 - len(displayable))]))
        geo_names = {
            name: OUTLINE_GEO_NAMES.get(name, name)
            for name in [country, *options]
        }
        challenges.append(_challenge(
            "border_battle", difficulty, _slug(country),
            {"prompt": f"Tap every country that shares a land border with {country}.",
             "country": country, "target_geo_name": geo_names[country], "countries": options,
             "geo_names": geo_names, "neighbors": displayable,
             "map_source": "Natural Earth 1:50m Admin 0 Countries"},
            sorted(displayable), f"{country} has {len(displayable)} land neighbours in this round: {', '.join(displayable)}.",
            {"name": "Natural Earth / CIA World Factbook", "url": "https://www.naturalearthdata.com/downloads/50m-cultural-vectors/50m-admin-0-countries/"},
        ))

    estimates = [
        ("What is the area of Greenland?", 2_166_086, 100_000, "km²", "2,166,086 km²", 1_000_000, 3_000_000, "Greenland's area is about 2.17 million km²."),
        ("About how long is the River Nile?", 6650, 500, "km", "about 6,650 km", 4_000, 8_000, "The Nile is commonly measured at about 6,650 km; river-length estimates can vary by source and method."),
        ("About what percentage of the world's population lives in Asia?", 59, 7, "%", "about 59%", 30, 80, "Roughly 59% of the world's population lives in Asia, based on recent UN regional estimates."),
        ("How far apart are London and New York, as the crow flies?", 5570, 500, "km", "about 5,570 km", 3_000, 7_000, "The great-circle distance is about 5,570 km; exact city points vary."),
        ("About how many people live in Tokyo Metropolis?", 14_000_000, 2_000_000, "people", "about 14 million", 5_000_000, 25_000_000, "Tokyo Metropolis has roughly 14 million residents; the wider metro area is much larger."),
        ("About how high is Mount Aconcagua?", 6961, 150, "m", "6,961 m", 5_000, 8_000, "Aconcagua reaches 6,961 metres above sea level in the Andes."),
        ("About how large is Lake Superior?", 82_100, 8_000, "km²", "82,100 km²", 40_000, 120_000, "Lake Superior covers about 82,100 km²."),
        ("About how long is the Great Wall of China, including branches?", 21_196, 2_500, "km", "about 21,196 km", 10_000, 30_000, "China's State Administration of Cultural Heritage reported a total length of 21,196 km in 2012."),
    ]
    estimate_difficulty = ("easy", "medium", "medium", "hard", "hard", "expert", "expert", "expert")
    sources = (
        {"name": "CIA World Factbook / UN / cited reference", "reference_year": "varies by fact"},
    )
    for index, (prompt, value, tolerance, unit, display, minimum, maximum, explanation) in enumerate(estimates):
        challenges.append(_challenge(
            "closest_wins", estimate_difficulty[index], f"estimate-{index + 1}",
            {"prompt": prompt, "min_value": minimum, "max_value": maximum, "unit": unit,
             "reference_year": "see explanation", "source_note": explanation},
            {"value": value, "tolerance": tolerance, "display": display},
            explanation, sources[0],
        ))
    return challenges


CHALLENGE_BANK = _build_challenges()


def get_challenge_bank():
    return CHALLENGE_BANK


def make_daily_challenge(date_string, used_ids=None, challenge_bank=None):
    used_ids = set(used_ids or [])
    challenge_bank = challenge_bank or CHALLENGE_BANK
    daily_seed = _seed(f"atlas-daily:{date_string}")
    candidates = {}
    for challenge in challenge_bank:
        candidates.setdefault(challenge["game_type"], []).append(challenge)
    rng = random.Random(daily_seed)
    game_types = [meta["id"] for meta in GAME_TYPES]
    omitted = game_types[daily_seed % len(game_types)]
    selected_types = [game_type for game_type in game_types if game_type != omitted]
    round_difficulties = ["easy", "medium", "medium", "hard", "hard", "expert", "expert"]
    rng.shuffle(selected_types)
    rounds = []
    for index, game_type in enumerate(selected_types):
        difficulty = round_difficulties[index]
        options = [
            item for item in candidates[game_type]
            if item["difficulty"] == difficulty and item["id"] not in used_ids
        ]
        if not options:
            options = [item for item in candidates[game_type] if item["difficulty"] == difficulty]
        if not options:
            options = candidates[game_type]
        chosen = rng.choice(sorted(options, key=lambda item: item["id"]))
        rounds.append(json.loads(json.dumps(chosen)))
        used_ids.add(chosen["id"])
    return rounds


def make_practice_challenge(game_type=None, difficulty="medium", seed=None, challenge_bank=None):
    if difficulty not in DIFFICULTIES:
        raise ValueError("Choose a supported difficulty.")
    valid_types = {meta["id"] for meta in GAME_TYPES}
    if game_type is not None and game_type not in valid_types:
        raise ValueError("Choose a supported mini-game.")
    challenge_bank = challenge_bank or CHALLENGE_BANK
    candidates = [
        challenge for challenge in challenge_bank
        if (game_type is None or challenge["game_type"] == game_type)
        and challenge["difficulty"] == difficulty
    ]
    if not candidates:
        raise ValueError(f"No {difficulty} challenges are available for this game.")
    return random.Random(seed).choice(candidates) if seed is not None else random.SystemRandom().choice(candidates)


def public_challenge(challenge, revealed_hints=0, attempts=0):
    payload = json.loads(json.dumps(challenge["payload"]))
    game_type = challenge["game_type"]
    hidden = ("clues", "accepted_answers", "answer_placeholder")
    if game_type in {"mystery_country", "country_outline", "where_in_world"}:
        hidden += ("country", "aliases")
    if game_type == "country_outline":
        hidden += ("geo_name", "source")
    if game_type == "where_in_world":
        hidden += ("landmark", "region", "photo_source")
    if game_type == "where_in_world":
        hidden += ("hints",)
    for key in hidden:
        payload.pop(key, None)
    if game_type == "mystery_country":
        clue_index = min(max(revealed_hints - 1, 0), len(challenge["payload"]["clues"]) - 1)
        payload["clue"] = challenge["payload"]["clues"][clue_index]
        payload["clues_revealed"] = min(max(revealed_hints, 1), len(challenge["payload"]["clues"]))
        payload["clue_count"] = len(challenge["payload"]["clues"])
        payload["guesses_remaining"] = max(0, 5 - attempts)
    elif game_type == "where_in_world":
        hint_index = min(max(revealed_hints - 1, 0), len(challenge["payload"]["hints"]) - 1)
        payload["hint"] = challenge["payload"]["hints"][hint_index] if revealed_hints else None
        payload["hint_revealed"] = bool(revealed_hints)
    elif game_type == "higher_lower":
        payload.pop("left_value", None)
        payload.pop("right_value", None)
    elif game_type == "border_battle":
        payload.pop("neighbors", None)
    elif game_type == "closest_wins":
        payload.pop("source_note", None)
    return {
        "id": challenge["id"],
        "game_type": game_type,
        "game_name": next(meta["name"] for meta in GAME_TYPES if meta["id"] == game_type),
        "difficulty": challenge["difficulty"],
        "prompt": payload.pop("prompt"),
        "payload": payload,
        "revealed_hints": revealed_hints,
        "mechanic": next(meta["mechanic"] for meta in GAME_TYPES if meta["id"] == game_type),
    }


def normalize_answer(value):
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def grade_challenge(challenge, answer, elapsed_seconds, revealed_hints=0):
    game_type = challenge["game_type"]
    expected = challenge["correct_answer"]
    payload = challenge["payload"]
    correct = False
    detail = {}
    if game_type == "higher_lower":
        correct = isinstance(answer, str) and answer in {"left", "right", "tie"} and answer == expected
        detail = {
            "left_value": payload["left_value"], "right_value": payload["right_value"],
            "left": payload["left"], "right": payload["right"], "unit": payload["unit"],
        }
    elif game_type in {"mystery_country", "country_outline", "where_in_world"}:
        if isinstance(answer, str):
            accepted = payload.get("accepted_answers", [expected])
            normalized = {normalize_answer(item) for item in [expected, *accepted]}
            correct = normalize_answer(answer) in normalized
        detail = {"correct_answer": expected}
    elif game_type == "closest_wins":
        value = answer.get("value") if isinstance(answer, dict) else answer
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            value = float(value)
            target = expected["value"]
            difference = abs(value - target)
            ratio = difference / max(target, 1)
            correct = difference <= expected["tolerance"]
            detail = {
                "guess": value, "difference": difference, "correct_value": target,
                "correct_display": expected["display"], "unit": payload["unit"],
            }
    elif game_type == "flag_connections":
        if isinstance(answer, list) and all(isinstance(item, str) for item in answer):
            selected = set(answer)
            expected_set = set(expected)
            correct = selected == expected_set
            timed_out = elapsed_seconds >= payload["timer_seconds"]
            precision = len(selected & expected_set) / max(len(selected), 1)
            recall = len(selected & expected_set) / max(len(expected_set), 1)
            detail = {"correct_countries": sorted(expected_set), "selected_count": len(selected),
                      "precision": precision, "recall": recall, "timed_out": timed_out}
            correct = correct and not timed_out
    elif game_type == "border_battle":
        if isinstance(answer, list) and all(isinstance(item, str) for item in answer):
            selected = set(answer)
            expected_set = set(expected)
            correct_count = len(selected & expected_set)
            false_count = len(selected - expected_set)
            detail = {"correct_countries": sorted(expected_set), "correct_selected": correct_count,
                      "incorrect_selected": false_count}
            correct = selected == expected_set
    elif game_type == "geography_connections":
        if isinstance(answer, str):
            normalized = normalize_answer(answer)
            accepted = payload.get("accepted_answers", [])
            correct = any(normalize_answer(item) in normalized for item in accepted)
        detail = {"correct_answer": expected}

    if game_type == "closest_wins" and detail:
        ratio = detail["difference"] / max(detail["correct_value"], 1)
        points = round(1000 * max(0, 1 - ratio * 3))
    elif game_type in {"flag_connections", "border_battle"} and detail:
        correct_count = (
            len(set(answer) & set(expected)) if isinstance(answer, list) else 0
        )
        false_count = len(set(answer) - set(expected)) if isinstance(answer, list) else 0
        points = 0 if detail.get("timed_out") else max(
            0, round(1000 * correct_count / max(len(expected), 1) - 180 * false_count)
        )
    else:
        points = 1000 if correct else 0
    if game_type == "mystery_country":
        attempts = max(0, int(revealed_hints) - 1)
        points = max(250, 1000 - attempts * 150) if correct else 0
    if game_type == "where_in_world" and revealed_hints:
        points = round(points * .8)
    speed_bonus = round(100 * max(0, 1 - max(0, elapsed_seconds) / 45)) if correct else 0
    points = min(1100, points + speed_bonus)
    detail["correct"] = correct
    detail["points"] = points
    detail["elapsed_seconds"] = round(max(0, elapsed_seconds), 2)
    detail["explanation"] = challenge["explanation"]
    if game_type in {"mystery_country", "country_outline", "where_in_world"}:
        detail["correct_answer_display"] = challenge["correct_answer"]
    return detail


def serialize_challenge(challenge):
    return json.dumps(challenge, ensure_ascii=False, separators=(",", ":"))
