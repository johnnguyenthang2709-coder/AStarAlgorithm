export const distance = (meters: number) => meters < 1000 ? `${Math.round(meters).toLocaleString()} m` : `${(meters / 1000).toFixed(2)} km`
export const score = (value: number) => Number.isInteger(value) ? String(value) : value.toFixed(2)
export const number = (value: number) => value.toLocaleString()
