let stocks = [];
let state = {cash: 0, holdings: {}};
let selected = null;
let side = 'buy';
const $ = id => document.getElementById(id);
const money = n => '$' + n.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});

function render() {
  if (!selected) return;
  const invested = stocks.reduce((n, s) => n + (state.holdings[s.symbol] || 0) * s.price, 0);
  $('portfolioValue').textContent = money(state.cash + invested);
  $('cash').textContent = money(state.cash);
  $('invested').textContent = money(invested);
  $('performance').textContent = 'Portfolio · demo market';
  $('stocks').innerHTML = stocks.map(s => `<button class="stock ${s.symbol === selected.symbol ? 'active' : ''}" data-symbol="${s.symbol}"><strong>${s.symbol}</strong><small>${s.name}</small><div class="price">${money(s.price)}</div><div class="change ${s.change >= 0 ? 'green' : 'red'}">${s.change >= 0 ? '+' : ''}${s.change}% today</div></button>`).join('');
  document.querySelectorAll('.stock').forEach(b => b.onclick = () => { selected = stocks.find(s => s.symbol === b.dataset.symbol); $('notice').textContent = ''; render(); });
  const held = stocks.filter(s => state.holdings[s.symbol] > 0);
  $('holdingCount').textContent = held.length + ' assets';
  $('holdings').innerHTML = held.length ? held.map(s => `<div class="row holding"><div class="ticker">${s.symbol[0]}</div><div class="holding-name"><strong>${s.symbol}</strong><small>${state.holdings[s.symbol]} shares · ${s.name}</small></div><div class="right"><strong>${money(state.holdings[s.symbol] * s.price)}</strong><small class="${s.change >= 0 ? 'green' : 'red'}" style="display:block;margin-top:4px">${s.change >= 0 ? '+' : ''}${s.change}%</small></div></div>`).join('') : '<p>No holdings yet. Pick a stock to get started.</p>';
  $('selectedName').textContent = selected.name;
  $('selectedSymbol').textContent = selected.symbol + ' · Stock';
  $('selectedPrice').textContent = money(selected.price);
  $('selectedChange').textContent = `${selected.change >= 0 ? '+' : ''}${selected.change}% today`;
  $('selectedChange').className = selected.change >= 0 ? 'green' : 'red';
  $('buyTab').classList.toggle('on', side === 'buy');
  $('sellTab').classList.toggle('on', side === 'sell');
  $('trade').textContent = side === 'buy' ? 'Buy shares' : 'Sell shares';
  $('trade').classList.toggle('sell', side === 'sell');
  const q = Number($('quantity').value);
  $('total').textContent = money(Number.isFinite(q) ? Math.max(0, q) * selected.price : 0);
  $('available').textContent = side === 'buy' ? money(state.cash) : `${state.holdings[selected.symbol] || 0} shares`;
}

async function loadState() {
  const response = await fetch('/api/state');
  if (!response.ok) throw new Error('Could not load account data.');
  const data = await response.json();
  stocks = data.stocks;
  state = data.portfolio;
  selected = stocks.find(s => s.symbol === selected?.symbol) || stocks[0];
  render();
}

$('buyTab').onclick = () => { side = 'buy'; $('notice').textContent = ''; render(); };
$('sellTab').onclick = () => { side = 'sell'; $('notice').textContent = ''; render(); };
$('quantity').oninput = render;
$('trade').onclick = async () => {
  const quantity = Number($('quantity').value);
  if (!Number.isSafeInteger(quantity) || quantity <= 0) { $('notice').textContent = 'Enter a positive whole number of shares.'; return; }
  $('trade').disabled = true;
  try {
    const response = await fetch('/api/trade', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({side, symbol: selected.symbol, quantity})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Trade failed.');
    stocks = data.state.stocks;
    state = data.state.portfolio;
    $('notice').textContent = `${side === 'buy' ? 'Bought' : 'Sold'} ${quantity} ${selected.symbol} share${quantity === 1 ? '' : 's'} for ${money(data.trade.total)} (simulation).`;
    render();
  } catch (error) {
    $('notice').textContent = error.message;
  } finally {
    $('trade').disabled = false;
  }
};

$('date').textContent = new Date().toLocaleDateString('en-US', {month: 'long', day: 'numeric', year: 'numeric'});
loadState().catch(error => { $('notice').textContent = error.message + ' Run python server.py and open http://127.0.0.1:8000.'; });
