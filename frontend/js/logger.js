export class Logger {
    constructor(module) {
        this.module = module;
        this.levels = {
            'INFO' : 0,
            'WARN' : 1,
            'ERROR' : 2,
            'DEBUG' : 3}
    }

    log(level, message, data = null) {
        const timestamp = new Date().toISOString();
        const logEntry = `[${timestamp}] [${this.module}] [${level}] ${message}`;
        
        switch (this.levels[level]) {
            case 0:
                console.log(logEntry);
            break;
            case 1:
                console.warn(logEntry);
            break;
            case 2:
                console.error(logEntry);
            break;
            case 3:
                console.debug(logEntry)
            break;

        }
        
    }

    info(message, data) { this.log('INFO', message, data); }
    warn(message, data) { this.log('WARN', message, data); }
    error(message, data) { this.log('ERROR', message, data); }
    debug(message, data) { if (this.isDev) this.log('DEBUG', message, data); }
}
