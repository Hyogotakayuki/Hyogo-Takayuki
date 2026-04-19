// Simple JSON file storage (no native compilation needed)
const fs = require('fs');
const path = require('path');

const DATA_PATH = path.join(__dirname, 'data', 'db.json');
const dataDir = path.join(__dirname, 'data');

if (!fs.existsSync(dataDir)) fs.mkdirSync(dataDir, { recursive: true });

const EMPTY = () => ({ users: [], assets: [], income_sources: [], expenses: [], transactions: [] });

function read() {
  if (!fs.existsSync(DATA_PATH)) return EMPTY();
  try {
    return JSON.parse(fs.readFileSync(DATA_PATH, 'utf8'));
  } catch (e) {
    return EMPTY();
  }
}

function write(data) {
  fs.writeFileSync(DATA_PATH, JSON.stringify(data, null, 2));
}

function nextId(arr) {
  return arr.length > 0 ? Math.max(...arr.map(r => r.id)) + 1 : 1;
}

module.exports = { read, write, nextId };
