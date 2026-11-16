// Pictures of the outfits for the wardrobe window (spec outfits): one flat drawing per outfit as an
// inline SVG, laid out like clothes on a table. Only fixed shapes and colours: no text from the server
// goes into the SVG, nothing is loaded from outside, nothing is random. An unknown id has no picture.

const INK = "#183740";

// a shirt with short sleeves, and a jacket with long sleeves (viewBox 0 0 120 120)
const SHORT = "M40 22 L27 26 L11 41 L22 55 L32 48 L32 104 Q60 109 88 104 L88 48 L98 55 L109 41 L93 26 L80 22 Q60 33 40 22 Z";
const LONG = "M40 20 L26 25 Q17 30 15 45 L10 99 L22 101 L32 58 L32 106 Q60 111 88 106 L88 58 L98 101 L110 99 L105 45 Q103 30 94 25 L80 20 Q60 30 40 20 Z";

const garment = (path, fill) => `<path d="${path}" fill="${fill}" stroke="${INK}" stroke-width="2.2" stroke-linejoin="round"/>`;

function hibiscus(x, y) {
  const petals = [0, 1, 2, 3, 4].map((k) => {
    const a = (k / 5) * Math.PI * 2 - Math.PI / 2;
    return `<ellipse cx="${(x + Math.cos(a) * 3.6).toFixed(1)}" cy="${(y + Math.sin(a) * 3.6).toFixed(1)}" rx="3" ry="2.2" transform="rotate(${(k * 72).toFixed(0)} ${(x + Math.cos(a) * 3.6).toFixed(1)} ${(y + Math.sin(a) * 3.6).toFixed(1)})" fill="#fff1dc"/>`;
  }).join("");
  return `<ellipse cx="${x + 6}" cy="${y + 4}" rx="4" ry="1.8" transform="rotate(30 ${x + 6} ${y + 4})" fill="#3f8f5a"/>${petals}<circle cx="${x}" cy="${y}" r="1.8" fill="#ffd23f"/>`;
}

const PICTURES = {
  basic: () => `
    ${garment(SHORT, "#bce65f")}
    <path d="M44 24 Q60 33 76 24" fill="none" stroke="#8fb43e" stroke-width="3"/>
    <rect x="33" y="44" width="54" height="5" fill="#173743" transform="rotate(12 60 46)" rx="2"/>`,
  hawaii: () => `
    <defs><clipPath id="w-hawaii"><path d="${SHORT}"/></clipPath></defs>
    ${garment(SHORT, "#e8573f")}
    <g clip-path="url(#w-hawaii)">
      ${[[45, 42], [75, 38], [60, 62], [42, 80], [78, 72], [55, 96], [86, 96], [20, 45], [100, 45]].map(([x, y]) => hibiscus(x, y)).join("")}
    </g>
    <path d="M40 22 L52 40 L60 30 L68 40 L80 22 Q60 33 40 22 Z" fill="#f07a62" stroke="${INK}" stroke-width="1.6" stroke-linejoin="round"/>
    <path d="M52 40 L60 30 L68 40 Z" fill="#c98b6a"/>
    <line x1="61" y1="42" x2="61" y2="104" stroke="${INK}" stroke-width="1" opacity=".45"/>
    ${[50, 64, 78, 92].map((y) => `<circle cx="64" cy="${y}" r="1.6" fill="#fff1dc" stroke="${INK}" stroke-width=".6"/>`).join("")}`,
  raincoat: () => `
    <path d="M42 22 Q38 4 60 3 Q82 4 78 22 Q60 30 42 22 Z" fill="#e2b11f" stroke="${INK}" stroke-width="2.2" stroke-linejoin="round"/>
    ${garment(LONG, "#f2c230")}
    <rect x="31" y="84" width="58" height="6" fill="#e3eaec" stroke="${INK}" stroke-width="1"/>
    <rect x="12" y="84" width="11" height="5" fill="#e3eaec" transform="rotate(6 17 86)"/>
    <rect x="97" y="84" width="11" height="5" fill="#e3eaec" transform="rotate(-6 102 86)"/>
    <line x1="60" y1="26" x2="60" y2="108" stroke="#b98d13" stroke-width="2.4"/>
    <rect x="57.5" y="30" width="5" height="7" rx="1.5" fill="#b98d13"/>
    <rect x="37" y="66" width="16" height="12" rx="2" fill="#e6b522" stroke="${INK}" stroke-width="1.2"/>
    <rect x="67" y="66" width="16" height="12" rx="2" fill="#e6b522" stroke="${INK}" stroke-width="1.2"/>
    <path d="M37 66 h16 v4 h-16 Z M67 66 h16 v4 h-16 Z" fill="#d4a51d"/>
    <path d="M54 24 l-2 12 M66 24 l2 12" stroke="${INK}" stroke-width="1.2"/>
    <circle cx="52" cy="37" r="1.6" fill="#ff7a59"/><circle cx="68" cy="37" r="1.6" fill="#ff7a59"/>`,
  tracksuit: () => `
    ${garment(LONG, "#1f3b73")}
    <path d="M27 27 Q19 33 17 46 L12 99" fill="none" stroke="#fff" stroke-width="2"/>
    <path d="M31 27 Q23 33 21 46 L16 99" fill="none" stroke="#fff" stroke-width="2"/>
    <path d="M93 27 Q101 33 103 46 L108 99" fill="none" stroke="#fff" stroke-width="2"/>
    <path d="M89 27 Q97 33 99 46 L104 99" fill="none" stroke="#fff" stroke-width="2"/>
    <rect x="46" y="12" width="28" height="12" rx="3" fill="#1f3b73" stroke="${INK}" stroke-width="2"/>
    <line x1="46" y1="21" x2="74" y2="21" stroke="#fff" stroke-width="1.6"/>
    <line x1="60" y1="13" x2="60" y2="108" stroke="#fff" stroke-width="2"/>
    <rect x="57.5" y="16" width="5" height="8" rx="1.5" fill="#fff"/>
    <rect x="31" y="98" width="58" height="8" fill="#18315f"/>
    <line x1="36" y1="72" x2="48" y2="80" stroke="#18315f" stroke-width="2"/>
    <line x1="84" y1="72" x2="72" y2="80" stroke="#18315f" stroke-width="2"/>`,
  blazer: () => `
    ${garment(LONG, "#2b3445")}
    <path d="M44 22 L60 30 L76 22 L66 70 L54 70 Z" fill="#f6f3ec" stroke="${INK}" stroke-width="1.4"/>
    <path d="M57 30 L63 30 L65 58 L60 66 L55 58 Z" fill="#8c2639" stroke="${INK}" stroke-width="1"/>
    <path d="M57 30 L63 30 L62 35 L58 35 Z" fill="#6d1c2c"/>
    <path d="M40 20 L48 36 L42 42 L57 78 L60 74 L44 22 Z" fill="#3e4a61" stroke="${INK}" stroke-width="1.4" stroke-linejoin="round"/>
    <path d="M80 20 L72 36 L78 42 L63 78 L60 74 L76 22 Z" fill="#3e4a61" stroke="${INK}" stroke-width="1.4" stroke-linejoin="round"/>
    <circle cx="60" cy="86" r="2.3" fill="#11161f"/><circle cx="60" cy="96" r="2.3" fill="#11161f"/>
    <path d="M73 52 h12 l-3 6 h-9 Z" fill="#f6f3ec" stroke="${INK}" stroke-width="1"/>
    <line x1="38" y1="88" x2="52" y2="88" stroke="#1d2431" stroke-width="2"/>
    <line x1="68" y1="88" x2="82" y2="88" stroke="#1d2431" stroke-width="2"/>
    ${[94, 98, 102].map((y) => `<circle cx="${y - 80}" cy="${y - 4}" r="1" fill="#9aa3b5"/>`).join("")}`,
};

// The picture of an outfit as an SVG string (empty for an id without one).
export function outfitPicture(id) {
  const draw = Object.hasOwn(PICTURES, id) ? PICTURES[id] : null;
  return draw ? `<svg class="outfit-pic" viewBox="0 0 120 120" role="img" aria-hidden="true">${draw()}</svg>` : "";
}
