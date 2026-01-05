async function getIdentity() {
  const res = await parentEpml.request('apiCall', {
    url: '/archive'
  })
  document.getElementById('output').textContent =
    JSON.stringify(res, null, 2)
}

document
  .getElementById('identityBtn')
  .addEventListener('click', getIdentity)
