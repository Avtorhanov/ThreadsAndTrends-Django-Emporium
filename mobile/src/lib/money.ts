/** Деньги приходят из API целыми копейками; рубли — только для отображения. */
export function formatKopecks(kopecks: number): string {
  const sign = kopecks < 0 ? "-" : "";
  const abs = Math.abs(kopecks);
  const rubles = String(Math.trunc(abs / 100)).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  const rest = abs % 100;
  const fraction = rest ? `,${String(rest).padStart(2, "0")}` : "";
  return `${sign}${rubles}${fraction} ₽`;
}
