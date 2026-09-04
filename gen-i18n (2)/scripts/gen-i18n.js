#!/usr/bin/env node

const fs = require('fs').promises;
const { createRequire } = require('module');
const path = require('path');

const DEFAULT_EXCLUDE_COLUMNS = ['Key', '提出时间', 'Desc'];

function showHelp() {
  console.log(`
Excel 多语言 JSON 生成工具

用法:
  node scripts/gen-i18n.js [选项]

选项:
  --excel, -e <path>       输入 Excel 文件，默认 ./origin.xlsx
  --output, -o <dir>       输出目录，默认 ./translation
  --exclude, -x <cols>     额外排除列，逗号分隔
  --empty-as, -m <value>   空单元格写入值，默认空字符串
  --keep-output, -k        保留输出目录中已有 JSON 文件
  --help, -h               显示帮助

示例:
  node scripts/gen-i18n.js
  node scripts/gen-i18n.js -e ./origin.xlsx -o ./locales
  node scripts/gen-i18n.js -e ./origin.xlsx -o ./locales -x Owner,Status
`);
}

function readValue(args, index, flag) {
  const value = args[index + 1];
  if (!value || value.startsWith('-')) {
    throw new Error(`${flag} 缺少参数值`);
  }
  return value;
}

function parseArgs(argv = process.argv.slice(2)) {
  const options = {
    excelPath: path.resolve(process.cwd(), 'origin.xlsx'),
    outputDir: path.resolve(process.cwd(), 'translation'),
    excludeColumns: [...DEFAULT_EXCLUDE_COLUMNS],
    emptyValue: '',
    clearOutput: true
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];

    if (arg === '--help' || arg === '-h') {
      options.help = true;
    } else if (arg === '--excel' || arg === '-e') {
      options.excelPath = path.resolve(process.cwd(), readValue(argv, i, arg));
      i += 1;
    } else if (arg === '--output' || arg === '-o') {
      options.outputDir = path.resolve(process.cwd(), readValue(argv, i, arg));
      i += 1;
    } else if (arg === '--exclude' || arg === '-x') {
      const cols = readValue(argv, i, arg)
        .split(',')
        .map((col) => col.trim())
        .filter(Boolean);
      options.excludeColumns = [...new Set([...options.excludeColumns, ...cols])];
      i += 1;
    } else if (arg === '--empty-as' || arg === '-m') {
      options.emptyValue = readValue(argv, i, arg);
      i += 1;
    } else if (arg === '--keep-output' || arg === '-k') {
      options.clearOutput = false;
    } else {
      throw new Error(`未知参数: ${arg}`);
    }
  }

  return options;
}

async function ensureExcelExists(excelPath) {
  try {
    const stat = await fs.stat(excelPath);
    if (!stat.isFile()) {
      throw new Error(`输入路径不是文件: ${excelPath}`);
    }
  } catch (error) {
    if (error.code === 'ENOENT') {
      throw new Error(`找不到 Excel 文件: ${excelPath}`);
    }
    throw error;
  }
}

async function clearJsonFiles(outputDir) {
  const entries = await fs.readdir(outputDir, { withFileTypes: true });
  const jsonFiles = entries
    .filter((entry) => entry.isFile() && entry.name.endsWith('.json'))
    .map((entry) => entry.name);

  await Promise.all(jsonFiles.map((file) => fs.unlink(path.join(outputDir, file))));
  return jsonFiles.length;
}

function normalizeCellValue(value, emptyValue) {
  if (value === undefined || value === null) {
    return emptyValue;
  }
  return String(value);
}

function loadXlsx() {
  try {
    return require('xlsx');
  } catch (error) {
    if (error.code !== 'MODULE_NOT_FOUND') {
      throw error;
    }
  }

  try {
    const requireFromCwd = createRequire(path.join(process.cwd(), 'package.json'));
    return requireFromCwd('xlsx');
  } catch (error) {
    if (error.code === 'MODULE_NOT_FOUND') {
      throw new Error('缺少依赖 xlsx，请先在当前项目安装: npm install xlsx');
    }
    throw error;
  }
}

async function generateI18nFiles(options = {}) {
  const xlsx = loadXlsx();

  const config = {
    excelPath: path.resolve(process.cwd(), 'origin.xlsx'),
    outputDir: path.resolve(process.cwd(), 'translation'),
    excludeColumns: [...DEFAULT_EXCLUDE_COLUMNS],
    emptyValue: '',
    clearOutput: true,
    ...options
  };

  await ensureExcelExists(config.excelPath);
  await fs.mkdir(config.outputDir, { recursive: true });

  let removedCount = 0;
  if (config.clearOutput) {
    removedCount = await clearJsonFiles(config.outputDir);
  }

  const workbook = xlsx.readFile(config.excelPath);
  const sheetName = workbook.SheetNames[0];
  if (!sheetName) {
    throw new Error('Excel 文件没有可读取的工作表');
  }

  const rows = xlsx.utils.sheet_to_json(workbook.Sheets[sheetName], { defval: undefined });
  if (rows.length === 0) {
    throw new Error('Excel 第一张工作表为空');
  }

  const headers = Object.keys(rows[0]);
  if (!headers.includes('Key')) {
    throw new Error('Excel 表头缺少必需的 Key 列');
  }

  const exclude = new Set(config.excludeColumns);
  const languages = headers.filter((header) => !exclude.has(header));
  if (languages.length === 0) {
    throw new Error('未检测到语言列');
  }

  const result = {
    success: true,
    sheetName,
    removedCount,
    rowCount: rows.length,
    languages,
    files: []
  };

  for (const language of languages) {
    const translations = {};

    for (const row of rows) {
      const key = normalizeCellValue(row.Key, '').trim();
      if (!key) {
        continue;
      }
      translations[key] = normalizeCellValue(row[language], config.emptyValue);
    }

    const filePath = path.join(config.outputDir, `${language}.json`);
    await fs.writeFile(filePath, `${JSON.stringify(translations, null, 2)}\n`, 'utf8');
    result.files.push(filePath);
  }

  return result;
}

async function main() {
  try {
    const options = parseArgs();
    if (options.help) {
      showHelp();
      return;
    }

    const result = await generateI18nFiles(options);
    console.log(`已读取工作表: ${result.sheetName}`);
    console.log(`已清理旧 JSON: ${result.removedCount}`);
    console.log(`已处理行数: ${result.rowCount}`);
    console.log(`已生成语言: ${result.languages.join(', ')}`);
    for (const file of result.files) {
      console.log(`- ${file}`);
    }
  } catch (error) {
    console.error(`生成失败: ${error.message}`);
    process.exitCode = 1;
  }
}

if (require.main === module) {
  main();
}

module.exports = {
  DEFAULT_EXCLUDE_COLUMNS,
  generateI18nFiles,
  parseArgs,
  showHelp
};
