export function fmtCustomer(contactName, companyName) {
  if (contactName) return `${contactName}--${companyName}`
  return companyName || ''
}
