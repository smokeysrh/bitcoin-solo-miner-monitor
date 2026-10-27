/**
 * Plain-language explanations for mining jargon. Shown by <Term> anywhere a newcomer might get stuck.
 * Keep each entry to one or two short sentences, no more jargon than the term itself.
 */
export interface GlossaryEntry {
  title: string
  body: string
}

export const GLOSSARY: Record<string, GlossaryEntry> = {
  solo: {
    title: 'Solo mining',
    body: 'You mine on your own instead of sharing work with a pool. Almost every day pays nothing, but if one of your hashes wins a block, you keep the whole reward.',
  },
  hashrate: {
    title: 'Hashrate',
    body: 'How many guesses per second your miners make. Bigger is better: 1 TH/s means one trillion guesses every second.',
  },
  difficulty: {
    title: 'Network difficulty',
    body: 'How hard the Bitcoin network currently makes it to find a block. It adjusts about every two weeks so a block shows up roughly every 10 minutes.',
  },
  share: {
    title: 'Share',
    body: 'A small proof of work your miner sends to the pool to show it is working. Most shares are far too small to be a block.',
  },
  bestshare: {
    title: 'Best share',
    body: 'The luckiest hash your miner has found so far. If it ever reaches the network difficulty, that hash is a block and you win the reward.',
  },
  rejected: {
    title: 'Rejected shares',
    body: 'Shares the pool refused, usually because they arrived late or were stale. A few percent is normal; a lot points to a network or pool problem.',
  },
  hwerrors: {
    title: 'Hardware errors',
    body: 'Hashes a chip computed incorrectly. A tiny rate is normal. A high rate usually means too much frequency, too little voltage or too much heat.',
  },
  efficiency: {
    title: 'Efficiency (J/TH)',
    body: 'Joules of electricity per terahash. Lower is better: a miner at 15 J/TH uses half the power of one at 30 J/TH for the same hashrate.',
  },
  node: {
    title: 'Bitcoin node',
    body: 'A computer that keeps its own copy of the blockchain. Mining to your own node means nobody else is involved in building your block.',
  },
  pool: {
    title: 'Solo pool',
    body: 'A server that hands your miners work and checks their shares. A solo pool does not share the reward: if you find a block, it pays you (minus a tiny fee).',
  },
  stratum: {
    title: 'Stratum',
    body: 'The language miners use to talk to a pool or node, written as stratum+tcp://host:port. The port is not the same as the web page port.',
  },
  fallback: {
    title: 'Fallback pool',
    body: 'A backup address the miner switches to when the main pool does not answer, so it keeps hashing instead of sitting idle.',
  },
  reward: {
    title: 'Block reward',
    body: 'The new bitcoin created by a block plus the transaction fees inside it. The new-coin part is cut in half roughly every four years.',
  },
  halving: {
    title: 'Halving',
    body: 'Every 210,000 blocks (about four years) the new-coin part of the reward is cut in half.',
  },
  retarget: {
    title: 'Difficulty adjustment',
    body: 'Every 2,016 blocks (about two weeks) the network recalculates difficulty from how fast the last blocks were found.',
  },
  mempool: {
    title: 'Mempool',
    body: 'The waiting room of transactions that have not been included in a block yet.',
  },
  odds: {
    title: 'Your odds',
    body: 'Each guess is an independent lottery ticket, so past results do not change your chances. The odds only depend on your hashrate and the network difficulty.',
  },
  psu: {
    title: 'PSU overhead',
    body: 'Power supplies waste some energy as heat, so the wall draws more than the miner reports. Add that percentage here for a truer electricity cost.',
  },
  frequency: {
    title: 'Frequency',
    body: 'How fast the chip is clocked in MHz. Higher means more hashrate but also more heat and power.',
  },
  coreVoltage: {
    title: 'Core voltage',
    body: 'The power level fed to the chip in millivolts. Too low and it makes errors at high frequency, too high and it runs hot.',
  },
  asic: {
    title: 'ASIC',
    body: 'A chip built only to compute Bitcoin hashes. It is thousands of times faster and more efficient than a computer processor at this one job.',
  },
  coinbase: {
    title: 'Payout address',
    body: 'Your Bitcoin address, used as the miner login. If you find a block, the reward is sent here, so double check it for typos.',
  },
  worker: {
    title: 'Worker name',
    body: 'A label after your address (address.worker) so the pool can show each miner separately.',
  },
}

export function lookup(key: string): GlossaryEntry | undefined {
  return GLOSSARY[key]
}
