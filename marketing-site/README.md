# TokenGuard — public marketing site

Static HTML/CSS/JS for strangers. Brand: **TokenGuard** (Coding Agent Token Guard).
Drop on Netlify or paste sections into a Gumroad product description.

## Pages

| File | Purpose |
| --- | --- |
| `index.html` | Landing — problem hook, simulated 75% proof, FAQ, Gumroad CTAs |
| `how-it-works.html` | Buy → install → integrate |
| `pricing.html` | $19 Gumroad zip + included Demo |
| `styles.css` | Self-contained dark theme |
| `config.js` | Rewrites `GUMROAD_URL` + optional local `APP_*` links |

## CTA targets

- Primary: Gumroad product URL (set in `config.js` after publish)
- Secondary/local: `{APP_ORIGIN}/app?demo=1` after buyer installs

## Deploy

Zip html/css/js (exclude `.netlify/`) and use Netlify Drop / `netlify deploy --allow-anonymous`.
