export function get_env_variable(
    name: string,
    def=undefined,
): string {
    let value = process.env[name] || def;
    if (value === undefined) {
        throw new Error(`Required environment variable ${name} is not set.`)
    }
    return value
}