export function getContractAddress(envKey: string): `0x${string}` {
  const v = process.env[envKey];
  if (!v || !/^0x[a-fA-F0-9]{40}$/.test(v)) {
    // Placeholder used until the contracts are deployed and addresses are set.
    return "0x0000000000000000000000000000000000000000";
  }
  return v as `0x${string}`;
}
