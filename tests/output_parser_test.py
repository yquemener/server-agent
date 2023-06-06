import json

from utils import extract_json

json_text = list()

json_text.append("""
 Yesterday, I had a great day exploring the mountains. The weather was perfect, with clear blue skies and a gentle breeze. As I hiked up the trail, I couldn't help but marvel at the breathtaking views. The rugged peaks and lush green valleys stretched out as far as the eye could see.

After a few hours of hiking, I found a cozy spot to rest and enjoy a packed lunch. While munching on a sandwich, I took out my notebook and started jotting down some thoughts. Here's an excerpt from my notes:

{
  "title": "Mountain Adventure",
  "date": "2023-06-05",
  "location": "XYZ Mountains"
}

Today's hike was simply incredible. The XYZ Mountains never fail to impress with their majestic beauty. I captured some stunning photographs along the way, and I can't wait to share them with my friends and family.

The trail was well-marked, and I encountered a few fellow hikers who were equally enthralled by the surroundings. We exchanged stories and tips for future hikes. It's amazing how nature can bring people together.

As the sun began to set, casting a warm golden glow over the landscape, I made my way back down the trail. The descent was just as rewarding, providing different perspectives and new surprises around every corner.

I arrived back at the trailhead feeling tired but fulfilled. The day spent in nature was exactly what I needed to recharge and reconnect. The mountains have a way of reminding us of our place in the world and the wonders that await us if we take the time to explore.

Overall, it was an unforgettable adventure, and I can't wait to embark on my next hiking journey. Until then, I'll cherish the memories I made in the XYZ Mountains and eagerly anticipate the next opportunity to immerse myself in nature's beauty.
""")

json_text.append("""
 Yesterday, I had a great day exploring the mountains. The weather was perfect, with clear blue skies and a gentle breeze. As I hiked up the trail, I couldn't help but marvel at the breathtaking views. The rugged peaks and lush green valleys stretched out as far as the eye could see.

After a few hours of hiking, I found a cozy spot to rest and enjoy a packed lunch. While munching on a sandwich, I took out my notebook and started jotting down some thoughts. Here's an excerpt from my notes:

```
{
  "title": "Mountain Adventure",
  "date": "2023-06-05",
  "location": "XYZ Mountains"
}
```

Today's hike was simply incredible. The XYZ Mountains never fail to impress with their majestic beauty. I captured some stunning photographs along the way, and I can't wait to share them with my friends and family.

The trail was well-marked, and I encountered a few fellow hikers who were equally enthralled by the surroundings. We exchanged stories and tips for future hikes. It's amazing how nature can bring people together.

As the sun began to set, casting a warm golden glow over the landscape, I made my way back down the trail. The descent was just as rewarding, providing different perspectives and new surprises around every corner.

I arrived back at the trailhead feeling tired but fulfilled. The day spent in nature was exactly what I needed to recharge and reconnect. The mountains have a way of reminding us of our place in the world and the wonders that await us if we take the time to explore.

Overall, it was an unforgettable adventure, and I can't wait to embark on my next hiking journey. Until then, I'll cherish the memories I made in the XYZ Mountains and eagerly anticipate the next opportunity to immerse myself in nature's beauty.
""")

json_text.append("""
 Yesterday, I had a great day exploring the mountains. The weather was perfect, with clear blue skies and a gentle breeze. As I hiked up the trail, I couldn't help but marvel at the breathtaking views. The rugged peaks and lush green valleys stretched out as far as the eye could see.

After a few hours of hiking, I found a cozy spot to rest and enjoy a packed lunch. While munching on a sandwich, I took out my notebook and started jotting down some thoughts. Here's an excerpt from my notes:

```json
{
  "title": "Mountain Adventure",
  "date": "2023-06-05",
  "location": "XYZ Mountains"
}
```

Today's hike was simply incredible. The XYZ Mountains never fail to impress with their majestic beauty. I captured some stunning photographs along the way, and I can't wait to share them with my friends and family.

The trail was well-marked, and I encountered a few fellow hikers who were equally enthralled by the surroundings. We exchanged stories and tips for future hikes. It's amazing how nature can bring people together.

As the sun began to set, casting a warm golden glow over the landscape, I made my way back down the trail. The descent was just as rewarding, providing different perspectives and new surprises around every corner.

I arrived back at the trailhead feeling tired but fulfilled. The day spent in nature was exactly what I needed to recharge and reconnect. The mountains have a way of reminding us of our place in the world and the wonders that await us if we take the time to explore.

Overall, it was an unforgettable adventure, and I can't wait to embark on my next hiking journey. Until then, I'll cherish the memories I made in the XYZ Mountains and eagerly anticipate the next opportunity to immerse myself in nature's beauty.
""")

json_text.append("""
 
 
 
  
  
""")


json_text.append("""
 Yesterday, I had a great day exploring the mountains. The weather was perfect, with clear blue skies and a gentle breeze. As I hiked up the trail, I couldn't help but marvel at the breathtaking views. The rugged peaks and lush green valleys stretched out as far as the eye could see.

After a few hours of hiking, I found a cozy spot to rest and enjoy a packed lunch. While munching on a sandwich, I took out my notebook and started jotting down some thoughts. Here's an excerpt from my notes:

Today's hike was simply incredible. The XYZ Mountains never fail to impress with their majestic beauty. I captured some stunning photographs along the way, and I can't wait to share them with my friends and family.

The trail was well-marked, and I encountered a few fellow hikers who were equally enthralled by the surroundings. We exchanged stories and tips for future hikes. It's amazing how nature can bring people together.

As the sun began to set, casting a warm golden glow over the landscape, I made my way back down the trail. The descent was just as rewarding, providing different perspectives and new surprises around every corner.

I arrived back at the trailhead feeling tired but fulfilled. The day spent in nature was exactly what I needed to recharge and reconnect. The mountains have a way of reminding us of our place in the world and the wonders that await us if we take the time to explore.

Overall, it was an unforgettable adventure, and I can't wait to embark on my next hiking journey. Until then, I'll cherish the memories I made in the XYZ Mountains and eagerly anticipate the next opportunity to immerse myself in nature's beauty.
""")

json_target = json.loads("""{
  "title": "Mountain Adventure",
  "date": "2023-06-05",
  "location": "XYZ Mountains"
}""")

assert(extract_json(json_text[0]) == json_target)
assert(extract_json(json_text[1]) == json_target)
assert(extract_json(json_text[2]) == json_target)
assert(extract_json(json_text[3]) is None)
assert(extract_json(json_text[4]) is None)


