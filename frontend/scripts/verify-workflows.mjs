import { createRequire } from 'node:module'
import assert from 'node:assert/strict'
const require = createRequire(import.meta.url)
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const base = process.env.QA_BASE_URL || 'http://127.0.0.1:5174'
const browser = await chromium.launch({ headless: true, channel: 'chrome' })
const errors = []
const results = []
// Esta prueba requiere la base aislada cargada mediante backend/scripts/seed_qa.py.
const contexts = []
async function login(role, viewport = { width: 1280, height: 900 }) {
  const context = await browser.newContext({ viewport })
  contexts.push(context)
  const page = await context.newPage()
  if (role === 'cashier') await page.clock.install()
  page.on('pageerror', error => errors.push(error.message))
  await page.goto(base + '/login')
  await page.getByLabel('Username', { exact: true }).fill('qa_' + role)
  await page.getByLabel('Password', { exact: true }).fill('QaPassword2026*')
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await page.waitForURL(base + '/' + role)
  results.push('Login and role routing: ' + role)
  return page
}
async function waitFor(check, label) {
  const until = Date.now() + 15000
  while (Date.now() < until) {
    if (await check()) { results.push(label); return }
    await new Promise(resolve => setTimeout(resolve, 100))
  }
  throw new Error('Failed: ' + label)
}
async function token(page) {
  return page.evaluate(() => localStorage.getItem('bar_inventory_access'))
}
async function api(page, method, path, data) {
  const response = await page.request.fetch(base + '/api' + path, {
    method, data, headers: { Authorization: 'Bearer ' + await token(page) },
  })
  assert(response.ok(), method + ' ' + path + ': ' + response.status())
  return response.json()
}
try {
  const admin = await login('admin')
  await admin.goto(base + '/catalog')
  await waitFor(async () => (await admin.locator('tbody tr').count()) === 30, 'Catalog loads all 30 products')
  await admin.getByLabel('Search by name').fill('QA Product 29')
  await waitFor(async () => (await admin.locator('tbody tr').count()) === 1, 'Catalog filters a product from page 2')
  await admin.goto(base + '/admin/tables')
  await waitFor(async () => (await admin.locator('tbody tr').count()) === 30, 'Table administration loads all 30 tables')
  await admin.screenshot({ path: '/private/tmp/bar-inventory-desktop.png', fullPage: true })

  const cashier = await login('cashier')
  await cashier.goto(base + '/inventory')
  await cashier.getByLabel('Product', { exact: false }).first().selectOption({ label: 'QA Product 00' })
  await cashier.getByLabel('Quantity received').fill('5')
  await cashier.getByRole('button', { name: 'Register entry', exact: true }).click()
  await cashier.getByRole('status').waitFor()
  await waitFor(async () => (await cashier.locator('tbody tr').filter({ hasText: 'QA Product 00' }).innerText()).includes('15'), 'Stock entry updates inventory to 15 units')
  await cashier.goto(base + '/cashier')

  const waiter = await login('waiter', { width: 390, height: 844 })
  await waiter.goto(base + '/room')
  await waitFor(async () => (await waiter.locator('main ul > li').count()) === 30, 'Mobile room displays all tables')
  const table = waiter.locator('main li').filter({ hasText: 'QA Table 00' })
  await table.getByRole('button', { name: 'Open order', exact: true }).click()
  await waiter.waitForURL(/\/orders\/\d+/)
  const orderId = Number(new URL(waiter.url()).pathname.split('/').pop())
  await waiter.getByRole('heading', { name: 'Add products', exact: true }).waitFor()
  const product = waiter.locator('main li').filter({ hasText: 'QA Product 00' })
  await product.getByRole('button', { name: 'Add', exact: true }).click()
  await waitFor(async () => (await waiter.locator('tbody tr').count()) === 1, 'Empty quantity adds one unit by default')
  await product.getByRole('button', { name: 'Add', exact: true }).click()
  await waitFor(async () => (await waiter.locator('tbody tr td').nth(1).innerText()) === '2', 'Repeated product accumulates quantity')
  await waiter.screenshot({ path: '/private/tmp/bar-inventory-mobile.png', fullPage: true })
  await waiter.getByRole('button', { name: 'Send to cashier', exact: true }).click()
  await waiter.getByRole('alertdialog').getByRole('button', { name: 'Send to cashier', exact: true }).click()
  await waiter.waitForURL(base + '/room')
  await table.getByRole('button', { name: 'View order', exact: true }).waitFor()
  results.push('Room keeps order access after sending to cashier')
  await waitFor(async () => await cashier.getByRole('link', { name: 'Order #' + orderId + ' - QA Table 00', exact: true }).isVisible(), 'Cashier receives pending order automatically')
  await cashier.getByRole('link', { name: 'Order #' + orderId + ' - QA Table 00', exact: true }).click()
  await cashier.getByText('This order has been sent to the cashier and can no longer be modified.').waitFor()
  assert.equal(await cashier.getByRole('heading', { name: 'Add products', exact: true }).count(), 0)
  results.push('Cashier order is read-only')

  await waiter.locator('main li').filter({ hasText: 'QA Table 01' }).getByRole('button', { name: 'Open order', exact: true }).click()
  await waiter.waitForURL(/\/orders\/\d+/)
  await waiter.getByRole('heading', { name: 'Add products', exact: true }).waitFor()
  await waiter.locator('main li').filter({ hasText: 'QA Product 00' }).getByRole('button', { name: 'Add', exact: true }).click()
  await waitFor(async () => (await waiter.locator('tbody tr').count()) === 1, 'Cancellation fixture contains an item')
  await waiter.getByRole('button', { name: 'Cancel order', exact: true }).click()
  await waiter.getByRole('alertdialog').getByRole('button', { name: 'Cancel order', exact: true }).click()
  await waiter.waitForURL(base + '/room')
  await waiter.locator('main li').filter({ hasText: 'QA Table 01' }).getByRole('button', { name: 'Open order', exact: true }).waitFor()
  const stock = await api(admin, 'GET', '/inventory/stock/')
  assert.equal(stock.results.find(row => row.product_name === 'QA Product 00').quantity, 13)
  results.push('Cancellation frees table and restores stock')

  await waiter.context().setOffline(true)
  await waiter.getByRole('alertdialog').waitFor()
  await waiter.context().setOffline(false)
  await waiter.waitForTimeout(3000)
  assert(await waiter.getByRole('alertdialog').isVisible())
  results.push('Connection warning persists after reconnection')
  await waiter.getByRole('button', { name: 'Understood', exact: true }).click()
  await waiter.waitForURL(base + '/login')
  results.push('Connection warning confirmation signs out')

  await cashier.goto(base + '/inventory')
  await cashier.getByRole('heading', { name: 'Inventory', exact: true }).waitFor()
  await cashier.clock.fastForward(180001)
  await cashier.waitForURL(base + '/login')
  results.push('Three minutes without interaction signs out despite polling')

  const disconnected = await login('waiter')
  const previousToken = await token(disconnected)
  await disconnected.context().setOffline(true)
  await disconnected.getByRole('alertdialog').waitFor()
  await disconnected.getByRole('button', { name: 'Understood', exact: true }).click()
  await disconnected.waitForURL(base + '/login')
  await waitFor(async () => await disconnected.evaluate(() =>
    JSON.parse(localStorage.getItem('bar_inventory_pending_closes') || '[]').length > 0),
    'Offline confirmation stores the pending server logout')
  await disconnected.context().setOffline(false)
  await waitFor(async () => await disconnected.evaluate(() =>
    JSON.parse(localStorage.getItem('bar_inventory_pending_closes') || '[]').length === 0),
    'Reconnection delivers the pending logout')
  const invalid = await disconnected.request.get(base + '/api/auth/me/', {
    headers: { Authorization: 'Bearer ' + previousToken },
  })
  assert.equal(invalid.status(), 401)
  results.push('Offline logout invalidates the old token on the server')

  const active = await login('cashier')
  await active.clock.fastForward(120000)
  await active.getByRole('link', { name: 'Home', exact: true }).click()
  await active.clock.fastForward(120000)
  assert.equal(new URL(active.url()).pathname, '/cashier')
  results.push('User interaction resets the inactivity timer')
  const activeToken = await token(active)
  await active.getByRole('button', { name: 'Sign out', exact: true }).click()
  await active.waitForURL(base + '/login')
  await waitFor(async () => (await active.request.get(base + '/api/auth/me/', {
    headers: { Authorization: 'Bearer ' + activeToken },
  })).status() === 401, 'Manual logout invalidates the server session')

  await admin.setViewportSize({ width: 390, height: 844 })
  await admin.goto(base + '/room')
  await admin.getByRole('heading', { name: 'Room - QA Venue', exact: true }).waitFor()
  assert(await admin.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth))
  results.push('Administrator menu fits mobile viewport')
  assert.deepEqual(errors, [])
  results.push('No uncaught browser errors')
  console.log(JSON.stringify({ passed: results.length, results }, null, 2))
} finally {
  await browser.close()
}
