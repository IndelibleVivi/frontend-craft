import { readFileSync, writeFileSync } from "node:fs";
const assets = new URL("../music-library/public/assets/", import.meta.url);
const image = (name) =>
  `data:image/jpeg;base64,${readFileSync(new URL(`originals/${name}.jpg`, assets)).toString("base64")}`;
const text = (x, y, size, value, color = "#171d21", extra = "") =>
  `<text x="${x}" y="${y}" fill="${color}" font-size="${size}" font-family="Arial, Helvetica, sans-serif" ${extra}>${value}</text>`;
const rect = (x, y, w, h, fill, extra = "") =>
  `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${fill}" ${extra}/>`;
const label = (n, color) =>
  text(
    36,
    565,
    12,
    `SIDE A SELECTIONS   /   ${String(n).padStart(2, "0")}`,
    color,
    'letter-spacing="2"',
  );
const covers = {
  "blue-hour":
    rect(0, 0, 600, 600, "#232d46") +
    `<image href="${image("manhattan")}" x="-80" y="-10" width="810" height="640" preserveAspectRatio="xMidYMid slice"/>` +
    text(
      34,
      110,
      92,
      "Blue",
      "#f4f2df",
      'font-weight="700" letter-spacing="-5"',
    ) +
    text(
      32,
      194,
      92,
      "Hour",
      "#f4f2df",
      'font-weight="700" letter-spacing="-5"',
    ) +
    text(40, 226, 12, "JAZZ AFTER DARK", "#dedcca", 'letter-spacing="3"') +
    label(1, "#f0ecda"),
  "soft-focus":
    rect(0, 0, 600, 600, "#efd3bc") +
    `<ellipse cx="360" cy="340" rx="215" ry="231" fill="#b95845"/><ellipse cx="412" cy="292" rx="149" ry="172" fill="#e6a459"/><ellipse cx="425" cy="250" rx="78" ry="125" fill="#f4d87a"/>` +
    text(
      30,
      123,
      112,
      "soft",
      "#302624",
      'font-weight="700" letter-spacing="-8"',
    ) +
    text(
      27,
      220,
      112,
      "focus",
      "#302624",
      'font-weight="700" letter-spacing="-8"',
    ) +
    text(38, 259, 12, "PIANO / STILLNESS", "#4d3730", 'letter-spacing="3"') +
    label(2, "#382827"),
  daytrip:
    rect(0, 0, 600, 600, "#efd858") +
    `<g transform="rotate(-32 300 300)">${rect(-100, 210, 850, 105, "#265482")}${rect(-100, 323, 850, 40, "#f9f0c9")}${rect(-100, 371, 850, 66, "#da6b3f")}</g>` +
    text(
      26,
      118,
      94,
      "DAYTRIP",
      "#25384b",
      'font-weight="900" letter-spacing="-5"',
    ) +
    text(
      34,
      160,
      12,
      "TAKE THE LONG WAY HOME",
      "#25384b",
      'letter-spacing="2"',
    ) +
    text(370, 529, 140, "↗", "#25384b") +
    label(3, "#25384b"),
  "floating-cities":
    rect(0, 0, 600, 600, "#03080b") +
    `<image href="${image("earth")}" x="85" y="140" width="750" height="750"/>` +
    text(
      34,
      68,
      34,
      "FLOATING",
      "#ecf5f4",
      'font-weight="500" letter-spacing="6"',
    ) +
    text(
      34,
      114,
      34,
      "CITIES",
      "#ecf5f4",
      'font-weight="500" letter-spacing="6"',
    ) +
    text(
      36,
      156,
      10,
      "THREE PERSPECTIVES ON A DISTANT HORIZON",
      "#b2c6cb",
      'letter-spacing="1"',
    ) +
    label(4, "#fff"),
  "after-hours":
    rect(0, 0, 600, 600, "#522e39") +
    `<g fill="none" stroke="#ef9166" stroke-width="5">${Array.from({ length: 21 }, (_, i) => `<ellipse cx="${112 + i * 14}" cy="${345 - i * 4}" rx="89" ry="153" transform="rotate(-28 ${112 + i * 14} ${345 - i * 4})"/>`).join("")}</g>` +
    text(
      31,
      81,
      52,
      "AFTER HOURS",
      "#ffe1b4",
      'font-weight="700" letter-spacing="-2"',
    ) +
    text(
      36,
      115,
      12,
      "VIBRAPHONE / ELECTRIC PIANO",
      "#ffe1b4",
      'letter-spacing="2"',
    ) +
    label(5, "#ffe1b4"),
  "good-company":
    rect(0, 0, 600, 600, "#b6cbb0") +
    text(
      30,
      96,
      75,
      "good",
      "#244a3f",
      'font-weight="800" letter-spacing="-4"',
    ) +
    text(
      29,
      173,
      75,
      "company",
      "#244a3f",
      'font-weight="800" letter-spacing="-4"',
    ) +
    `<g fill="#ec6e38" transform="translate(304 360)">${Array.from({ length: 8 }, (_, i) => `<ellipse cy="-89" rx="46" ry="92" transform="rotate(${i * 45})"/>`).join("")}<circle r="56" fill="#f1deab"/></g>` +
    label(6, "#244a3f"),
  "slow-motion":
    rect(0, 0, 600, 600, "#e5e5dc") +
    `<g stroke="#2d535e" stroke-width="1.5">${Array.from({ length: 38 }, (_, i) => `<path d="M ${i * 19 - 170} 600 L ${i * 19 + 260} 0"/>`).join("")}</g>` +
    rect(35, 35, 342, 218, "#e5e5dc") +
    text(48, 113, 58, "SLOW", "#254d59", 'letter-spacing="4"') +
    text(48, 181, 58, "MOTION", "#254d59", 'letter-spacing="1"') +
    text(
      49,
      222,
      11,
      "ERIK SATIE / KEVIN MACLEOD",
      "#254d59",
      'letter-spacing="1"',
    ) +
    `<circle cx="450" cy="452" r="102" fill="#d36543"/>` +
    rect(23, 542, 313, 38, "#e5e5dc") +
    label(7, "#254d59"),
  "electric-garden":
    rect(0, 0, 600, 600, "#e6abce") +
    `<g fill="#722c60">${[
      [164, 278, -35],
      [428, 374, 30],
      [315, 490, -55],
    ]
      .map(
        ([x, y, r]) =>
          `<g transform="translate(${x} ${y}) rotate(${r})"><ellipse rx="55" ry="155"/><ellipse rx="155" ry="55"/><ellipse rx="48" ry="132" transform="rotate(45)"/><ellipse rx="48" ry="132" transform="rotate(-45)"/><circle r="35" fill="#dbeb71"/></g>`,
      )
      .join("")}</g>` +
    text(
      30,
      65,
      44,
      "ELECTRIC",
      "#592e55",
      'font-weight="800" letter-spacing="-2"',
    ) +
    text(
      30,
      110,
      44,
      "GARDEN",
      "#592e55",
      'font-weight="800" letter-spacing="-2"',
    ) +
    label(8, "#251c31"),
};
for (const [name, body] of Object.entries(covers))
  writeFileSync(
    new URL(`covers/${name}.svg`, assets),
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 600" width="600" height="600" role="img"><title>${name.replaceAll("-", " ")}</title>${body}</svg>\n`,
  );
writeFileSync(
  new URL("mark.svg", assets),
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40"><rect width="40" height="40" rx="10" fill="#ec5c36"/><path d="M10 30 20 8 30 30M14 23h12" fill="none" stroke="#fff" stroke-width="4"/></svg>',
);
