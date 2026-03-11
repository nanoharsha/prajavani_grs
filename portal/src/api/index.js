const BASE = '/api/method/prajavani_grs.grs.api'

async function call(method, params = {}) {
  const url = new URL(`${BASE}.${method}`, location.origin)
  Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v))
  const res = await fetch(url, { headers: { Accept: 'application/json' } })
  if (!res.ok) throw new Error(`API error ${res.status}`)
  const data = await res.json()
  if (data.exc) throw new Error(data.exc)
  return data.message
}

async function post(method, params = {}) {
  const url = `${BASE}.${method}`
  const body = new URLSearchParams(params)
  const res = await fetch(url, {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })
  if (!res.ok) throw new Error(`API error ${res.status}`)
  const data = await res.json()
  if (data.exc) throw new Error(data.exc)
  return data.message
}

export const api = {
  trackGrievance:   (registration_no) => call('track_grievance', { registration_no }),
  getDepartments:   ()                 => call('get_departments'),
  getCategories:    (department)       => call('get_categories', { department }),
  getSubCategories: (category)         => call('get_sub_categories', { category }),
  submitGrievance:  (payload)          => post('submit_grievance', payload),
}
