const JSDOMEnvironment = require('jest-environment-jsdom');

class CustomJSDOMEnvironment extends JSDOMEnvironment {
  constructor(config, context) {
    const mergedConfig = {
      ...config,
      testEnvironmentOptions: config.testEnvironmentOptions ?? {},
      testURL: config.testURL ?? 'http://localhost',
    };
    mergedConfig.testEnvironmentOptions =
      mergedConfig.testEnvironmentOptions || {};
    if (!mergedConfig.testEnvironmentOptions.url) {
      mergedConfig.testEnvironmentOptions.url = mergedConfig.testURL;
    }
    super(mergedConfig, context);
  }
}

module.exports = CustomJSDOMEnvironment;
