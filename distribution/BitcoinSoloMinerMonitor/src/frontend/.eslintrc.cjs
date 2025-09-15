/* eslint-env node */
module.exports = {
  root: true,
  env: {
    node: true,
    browser: true,
    es2022: true,
  },
  extends: [
    "eslint:recommended",
    "plugin:vue/vue3-essential",
    "@vue/eslint-config-prettier",
  ],
  plugins: ["vue"],
  parserOptions: {
    ecmaVersion: "latest",
    sourceType: "module",
  },
  rules: {
    // Vue.js specific rules
    "vue/multi-word-component-names": "off",
    "vue/no-unused-vars": "warn",
    "vue/no-multiple-template-root": "off",
    "vue/valid-v-slot": "off",
    "vue/no-mutating-props": "warn",
    "vue/no-dupe-keys": "error",
    "vue/no-computed-properties-in-data": "warn",

    // JavaScript rules
    "no-console": process.env.NODE_ENV === "production" ? "warn" : "off",
    "no-debugger": process.env.NODE_ENV === "production" ? "warn" : "off",
    "no-unused-vars": [
      "warn",
      {
        argsIgnorePattern: "^_",
        varsIgnorePattern: "^_",
      },
    ],

    // Import/Export rules
    "no-undef": "error",

    // Code style
    "prefer-const": "warn",
    "no-var": "warn",
  },
  overrides: [
    {
      files: ["*.vue"],
      parser: "vue-eslint-parser",
      parserOptions: {
        parser: "@babel/eslint-parser",
        requireConfigFile: false,
        babelOptions: {
          presets: ["@babel/preset-env"],
        },
        ecmaVersion: 2022,
        sourceType: "module",
      },
    },
  ],
  ignorePatterns: ["dist/", "node_modules/", "*.min.js"],
};
