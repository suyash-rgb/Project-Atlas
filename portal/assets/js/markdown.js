(function (global) {
    'use strict';

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function renderInlineMarkdown(value) {
        return escapeHtml(value).split(/(`[^`]+`)/g).map(function (part) {
            if (part.charAt(0) === '`' && part.charAt(part.length - 1) === '`') {
                return '<code>' + part.slice(1, -1) + '</code>';
            }

            return part
                .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
                .replace(/__(.+?)__/g, '<strong>$1</strong>')
                .replace(/~~(.+?)~~/g, '<del>$1</del>')
                .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
                    '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
                .replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>')
                .replace(/(^|[^_])_([^_\n]+)_/g, '$1<em>$2</em>');
        }).join('');
    }

    function isTableDelimiter(line) {
        return /^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line);
    }

    function isTableStart(lines, index) {
        return index + 1 < lines.length &&
            lines[index].indexOf('|') !== -1 &&
            isTableDelimiter(lines[index + 1]);
    }

    function tableCells(line) {
        var value = line.trim();
        if (value.charAt(0) === '|') value = value.slice(1);
        if (value.charAt(value.length - 1) === '|') value = value.slice(0, -1);
        return value.split('|').map(function (cell) {
            return cell.trim();
        });
    }

    function isBlockStart(lines, index) {
        var line = lines[index];
        return /^\s*(?:#{1,6}\s|```|>|[-*+]\s+|\d+[.)]\s+)/.test(line) ||
            isTableStart(lines, index);
    }

    function renderTable(lines, start) {
        var headers = tableCells(lines[start]);
        var alignments = tableCells(lines[start + 1]).map(function (cell) {
            if (/^:-+:$/.test(cell)) return 'center';
            if (/^-+:$/.test(cell)) return 'right';
            return 'left';
        });
        var rows = [];
        var index = start + 2;

        while (index < lines.length && lines[index].trim() && lines[index].indexOf('|') !== -1) {
            rows.push(tableCells(lines[index]));
            index += 1;
        }

        var html = '<div class="markdown-table-wrapper"><table class="markdown-table"><thead><tr>';
        headers.forEach(function (header, cellIndex) {
            html += '<th style="text-align:' + (alignments[cellIndex] || 'left') + '">' +
                renderInlineMarkdown(header) + '</th>';
        });
        html += '</tr></thead><tbody>';

        rows.forEach(function (row) {
            html += '<tr>';
            headers.forEach(function (_, cellIndex) {
                html += '<td style="text-align:' + (alignments[cellIndex] || 'left') + '">' +
                    renderInlineMarkdown(row[cellIndex] || '') + '</td>';
            });
            html += '</tr>';
        });

        html += '</tbody></table></div>';
        return { html: html, next: index };
    }

    function renderAtlasMarkdown(markdown) {
        var lines = String(markdown == null ? '' : markdown)
            .replace(/\r\n?/g, '\n')
            .split('\n');
        var html = '';
        var index = 0;

        while (index < lines.length) {
            var line = lines[index];
            if (!line.trim()) {
                index += 1;
                continue;
            }

            if (/^\s*```/.test(line)) {
                var codeLines = [];
                index += 1;
                while (index < lines.length && !/^\s*```\s*$/.test(lines[index])) {
                    codeLines.push(lines[index]);
                    index += 1;
                }
                if (index < lines.length) index += 1;
                html += '<pre><code>' + escapeHtml(codeLines.join('\n')) + '</code></pre>';
                continue;
            }

            if (isTableStart(lines, index)) {
                var table = renderTable(lines, index);
                html += table.html;
                index = table.next;
                continue;
            }

            var heading = line.match(/^\s*(#{1,6})\s+(.+?)\s*#*\s*$/);
            if (heading) {
                var level = heading[1].length;
                html += '<h' + level + '>' + renderInlineMarkdown(heading[2]) + '</h' + level + '>';
                index += 1;
                continue;
            }

            if (/^\s*(?:[-*_]\s*){3,}$/.test(line)) {
                html += '<hr>';
                index += 1;
                continue;
            }

            if (/^\s*>\s?/.test(line)) {
                var quoteLines = [];
                while (index < lines.length && /^\s*>\s?/.test(lines[index])) {
                    quoteLines.push(lines[index].replace(/^\s*>\s?/, ''));
                    index += 1;
                }
                html += '<blockquote><p>' +
                    quoteLines.map(renderInlineMarkdown).join('<br>') +
                    '</p></blockquote>';
                continue;
            }

            var listMatch = line.match(/^\s*([-*+]|\d+[.)])\s+(.+)$/);
            if (listMatch) {
                var ordered = /^\d/.test(listMatch[1]);
                var listTag = ordered ? 'ol' : 'ul';
                html += '<' + listTag + '>';
                while (index < lines.length) {
                    var item = lines[index].match(/^\s*([-*+]|\d+[.)])\s+(.+)$/);
                    if (!item || /^\d/.test(item[1]) !== ordered) break;
                    html += '<li>' + renderInlineMarkdown(item[2]) + '</li>';
                    index += 1;
                }
                html += '</' + listTag + '>';
                continue;
            }

            var paragraph = [];
            while (index < lines.length && lines[index].trim() && !isBlockStart(lines, index)) {
                paragraph.push(lines[index]);
                index += 1;
            }
            if (paragraph.length === 0) {
                paragraph.push(lines[index]);
                index += 1;
            }
            html += '<p>' + paragraph.map(renderInlineMarkdown).join('<br>') + '</p>';
        }

        return html;
    }

    global.renderAtlasMarkdown = renderAtlasMarkdown;
}(window));
