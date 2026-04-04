import { useState, useRef, useCallback, useEffect, type FC } from 'react';

interface SearchableDropdownProps {
    options: string[];
    value: string;
    onChange: (value: string) => void;
    placeholder?: string;
    allowFreeText?: boolean;       // allow typing values not in the list
    multiple?: boolean;            // comma-separated multi-select
}

const SearchableDropdown: FC<SearchableDropdownProps> = ({
    options,
    value,
    onChange,
    placeholder = 'Type to search...',
    allowFreeText = false,
    multiple = false,
}) => {
    const [open, setOpen] = useState(false);
    const [search, setSearch] = useState('');
    const inputRef = useRef<HTMLInputElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    const selectedParts = multiple
        ? value.split(',').map(s => s.trim()).filter(Boolean)
        : [];
    const hasTrailingComma = multiple ? /,\s*$/.test(value) : false;
    const currentToken = multiple
        ? (hasTrailingComma ? '' : (value.split(',').pop()?.trim() ?? ''))
        : value;
    const committedSelections = multiple
        ? (hasTrailingComma ? selectedParts : selectedParts.slice(0, -1))
        : [];

    const filtered = options.filter(opt => {
        if (!multiple) {
            return opt.toLowerCase().includes((search || value).toLowerCase());
        }

        const isAlreadySelected = committedSelections.includes(opt);
        const tokenLower = currentToken.toLowerCase();
        const matchesToken = tokenLower.length === 0 || opt.toLowerCase().includes(tokenLower);

        if (isAlreadySelected) {
            return false;
        }

        return matchesToken;
    });

    const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const v = e.target.value;
        if (multiple) {
            onChange(v);
        } else {
            setSearch(v);
            if (allowFreeText) onChange(v);
        }
        setOpen(true);
    }, [onChange, allowFreeText, multiple]);

    const handleSelect = useCallback((opt: string) => {
        if (multiple) {
            const parts = value.split(',').map(s => s.trim()).filter(Boolean);
            parts.pop(); // remove the partial token
            parts.push(opt);
            onChange(parts.join(', ') + ', ');
        } else {
            onChange(opt);
            setSearch('');
        }
        setOpen(false);
        inputRef.current?.focus();
    }, [onChange, value, multiple]);

    // Close on click outside
    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
                setOpen(false);
            }
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, []);

    return (
        <div className="sd-container" ref={containerRef}>
            <input
                ref={inputRef}
                className="sd-input"
                value={multiple ? value : (search || value)}
                onChange={handleInputChange}
                onFocus={() => setOpen(true)}
                placeholder={placeholder}
                autoComplete="off"
            />
            <svg className="sd-chevron" width="10" height="6" viewBox="0 0 10 6" fill="none">
                <path d="M1 1l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            {open && filtered.length > 0 && (
                <div className="sd-dropdown">
                    {filtered.map(opt => (
                        <div
                            key={opt}
                            className={`sd-option ${multiple ? (committedSelections.includes(opt) ? 'selected' : '') : (opt === value ? 'selected' : '')}`}
                            onMouseDown={(e) => { e.preventDefault(); handleSelect(opt); }}
                        >
                            {opt}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default SearchableDropdown;
