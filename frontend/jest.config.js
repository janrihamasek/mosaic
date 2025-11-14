/** @type {import('jest').Config} */
module.exports = {
  preset: 'ts-jest/presets/js-with-ts',
  testEnvironment: '<rootDir>/jest.environment.js',
  setupFilesAfterEnv: ['<rootDir>/src/jest.setup.ts'],
  moduleNameMapper: {
    '\\.(css|scss|sass|less)$': 'identity-obj-proxy',
  },
  testEnvironmentOptions: {
    url: 'http://localhost',
  },
};
