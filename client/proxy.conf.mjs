// Dev server proxy: /api goes to the Flask API.
// `make serve` (scripts/serve.py) sets NEVERDIE_API_URL from the Neverdie
// configuration (port of etc/neverdie.yml, NEVERDIE_PORT...).
export default {
  '/api': {
    target: process.env.NEVERDIE_API_URL || 'http://127.0.0.1:5000',
    secure: false,
  },
};
