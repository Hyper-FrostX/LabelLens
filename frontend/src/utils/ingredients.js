export function splitIngredientsText(text) {
  if (!text?.trim()) return [];

  const ingredients = [];
  const delimiters = [];
  let start = 0;
  const closingFor = { "(": ")", "[": "]" };
  const closingCharacters = new Set(Object.values(closingFor));

  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];

    if (closingFor[character]) {
      delimiters.push(closingFor[character]);
    } else if (closingCharacters.has(character)) {
      if (delimiters.pop() !== character) return [];
    } else if (character === "," && delimiters.length === 0) {
      const ingredient = text.slice(start, index).trim();
      if (!ingredient) return [];
      ingredients.push(ingredient);
      start = index + 1;
    }
  }

  if (delimiters.length > 0) return [];
  const finalIngredient = text.slice(start).trim();
  if (!finalIngredient) return [];
  ingredients.push(finalIngredient);
  return ingredients;
}
