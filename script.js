let extractedTransactions = [];

async function processPDF() {

  const fileInput =
    document.getElementById('pdfUpload');

  if (!fileInput.files.length) {

    alert("Please upload a PDF");

    return;
  }

  const file =
    fileInput.files[0];

  const status =
    document.getElementById('status');

  status.innerHTML =
    "Loading PDF...";

  const arrayBuffer =
    await file.arrayBuffer();

  const pdf =
    await pdfjsLib.getDocument({
      data: arrayBuffer
    }).promise;

  let fullText = "";

  const maxPages =
    Math.min(pdf.numPages, 5);

  for (
    let pageNum = 1;
    pageNum <= maxPages;
    pageNum++
  ) {

    status.innerHTML =
      `Processing page ${pageNum} of ${maxPages}...`;

    const page =
      await pdf.getPage(pageNum);

    const viewport =
      page.getViewport({
        scale: 3
      });

    const canvas =
      document.createElement('canvas');

    const context =
      canvas.getContext('2d');

    canvas.height =
      viewport.height;

    canvas.width =
      viewport.width;

    await page.render({
      canvasContext: context,
      viewport: viewport
    }).promise;

    const result =
      await Tesseract.recognize(
        canvas,
        'eng'
      );

    fullText +=
      result.data.text + "\n";
  }

  document.getElementById(
    'ocrOutput'
  ).value = fullText;

  status.innerHTML =
    "Extracting transactions...";

  extractTransactions(fullText);

  status.innerHTML =
    `Done. Found ${extractedTransactions.length} transactions.`;
}

function extractTransactions(text) {

  extractedTransactions = [];

  const tbody =
    document.querySelector(
      '#resultsTable tbody'
    );

  tbody.innerHTML = "";

  const lines =
    text
      .split('\n')
      .map(l => l.trim())
      .filter(l => l.length > 0);

  let statementYear = "2022";

  const statementMatch =
    text.match(
      /Statement from .*? (\d{4})/i
    );

  if (statementMatch) {

    statementYear =
      statementMatch[1];
  }

  for (let i = 0; i < lines.length; i++) {

    const line =
      lines[i];

    const amountMatch =
      line.match(
        /([\d,]+\.\d{2})-?/
      );

    const balanceMatch =
      line.match(
        /(\d{1,3}(,\d{3})*\.\d{2})$/
      );

    const dateMatch =
      line.match(
        /0(\d{3})/
      );

    if (
      amountMatch &&
      balanceMatch &&
      dateMatch
    ) {

      const amount =
        amountMatch[1]
          .replace(/,/g, '');

      const rawDate =
        dateMatch[1];

      const month =
        rawDate.substring(0, 2);

      const day =
        rawDate.substring(2, 4);

      const formattedDate =
        `${statementYear}-${month}-${day}`;

      let description = "";

      if (lines[i + 1]) {

        description =
          lines[i + 1];

        if (
          lines[i + 2] &&
          !lines[i + 2].match(/0\d{3}/)
        ) {

          description +=
            " " + lines[i + 2];
        }
      }

      description =
        description
          .replace(/\s+/g, ' ')
          .trim();

      const transaction = {

        date: formattedDate,
        description,
        amount
      };

      extractedTransactions.push(
        transaction
      );

      const row =
        document.createElement('tr');

      row.innerHTML = `
        <td>${formattedDate}</td>
        <td>${description}</td>
        <td>${amount}</td>
      `;

      tbody.appendChild(row);
    }
  }
}

function downloadCSV() {

  if (!extractedTransactions.length) {

    alert("No transactions found");

    return;
  }

  let csv =
    "Date,Description,Amount\n";

  extractedTransactions.forEach(t => {

    csv +=
      `${t.date},"${t.description}",${t.amount}\n`;
  });

  const blob =
    new Blob(
      [csv],
      {
        type: 'text/csv'
      }
    );

  const link =
    document.createElement('a');

  link.href =
    URL.createObjectURL(blob);

  link.download =
    "transactions.csv";

  link.click();
}
