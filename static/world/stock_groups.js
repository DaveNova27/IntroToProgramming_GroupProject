// The stock card's rows grouped by shop (specs/stock-by-shop.md). Pure: no drawing, no DOM, so Node
// can test it. Which product belongs to which shop comes from the server (shops[i].products); the
// screen decides nothing about it.

// products: the owned products in catalogue order (state.products); shops: state.shops in shop order.
// Returns [{shop, name, heading, products}]: one group per unlocked shop that has a product, in shop
// order, the products in the order they came. A product no unlocked shop names is kept in a last group
// without a name, so nothing in stock disappears from the card. `heading` is the text to show above
// the group: the shop's name once there are two groups or more, else "" (the Cafe alone looks as
// before). The inputs are not changed.
export function stockGroups(products, shops) {
  const groups = [];
  const placed = new Set();
  for (const shop of shops) {
    if (!shop.unlocked) continue;
    const ids = new Set(shop.products);
    const mine = products.filter((p) => ids.has(p.id) && !placed.has(p.id));
    if (!mine.length) continue;
    for (const p of mine) placed.add(p.id);
    groups.push({ shop: shop.id, name: shop.name, products: mine });
  }
  const rest = products.filter((p) => !placed.has(p.id));
  if (rest.length) groups.push({ shop: null, name: "", products: rest });
  const headed = groups.length > 1;
  return groups.map((g) => ({ ...g, heading: headed ? g.name : "" }));
}
