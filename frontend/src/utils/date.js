export function formatDate(isoString) {
  if (!isoString) return null

  const date = new Date(isoString)
  if (Number.isNaN(date.getTime())) return null

  const day = String(date.getDate()).padStart(2, '0')
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  const month = months[date.getMonth()]
  const year = date.getFullYear()

  let hours = date.getHours()
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const period = hours >= 12 ? 'PM' : 'AM'
  hours = hours % 12
  if (hours === 0) hours = 12
  const hoursStr = String(hours).padStart(2, '0')

  return `${day} ${month} ${year}, ${hoursStr}:${minutes} ${period}`
}
