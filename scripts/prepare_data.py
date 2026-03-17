import pandas as pd
import numpy as np
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

def load_and_explore():
    """Load all CSV files in the data directory and show their structure"""
    print("--- Available CSV Files ---\n")
    csv_files = {}
    for f in os.listdir(DATA_DIR):
        if f.endswith('.csv'):
            path = os.path.join(DATA_DIR, f)
            try:
                df = pd.read_csv(path, encoding='utf-8', on_bad_lines='skip')
            except UnicodeDecodeError:
                df = pd.read_csv(path, encoding='latin-1', on_bad_lines='skip')
            csv_files[f] = df
            print(f"File: {f}")
            print(f"  Shape: {df.shape[0]} rows, {df.shape[1]} columns")
            print(f"  Columns: {df.columns.tolist()}")
            print()
    return csv_files

def prepare_pokemon_data(csv_files):
    #trying to find the main dataset ie whichever has the most rows or NAME column
    main_df = None
    main_name = None
    for name, df in csv_files.items():
        cols_lower = [c.lower() for c in df.columns]
        if 'name' in cols_lower or 'pokemon' in cols_lower:
            if main_df is None or len(df) > len(main_df):
                main_df = df
                main_name = name
    
    if main_df is None:
        # use the largest file in the data folder
        main_name = max(csv_files.keys(), key=lambda k: len(csv_files[k]))
        main_df = csv_files[main_name]
    
    print(f"Using primary dataset: {main_name} ({len(main_df)} rows)")
    print(f"Columns: {main_df.columns.tolist()}\n")
    
    df = main_df.copy()
    
    # standardizing the column names in lowercase and replacing spaces with underscores for easier handling
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('.', '_')
    
    print(f"Standardized columns: {df.columns.tolist()}\n")
    
    # identify key columns dynamically
    col_map = {}
    for col in df.columns:
        cl = col.lower()
        if cl in ['name', 'pokemon', 'pokemon_name']:
            col_map['name'] = col
        elif cl in ['type1', 'type_1', 'primary_type', 'type 1']:
            col_map['type1'] = col
        elif cl in ['type2', 'type_2', 'secondary_type', 'type 2']:
            col_map['type2'] = col
        elif cl in ['generation', 'gen', 'generation_number']:
            col_map['generation'] = col
        elif cl in ['hp', 'health']:
            col_map['hp'] = col
        elif cl in ['attack', 'atk', 'att']:
            col_map['attack'] = col
        elif cl in ['defense', 'defence', 'def']:
            col_map['defense'] = col
        elif cl in ['sp_attack', 'sp__atk', 'sp_atk', 'special_attack', 'spatk', 'sp__attack']:
            col_map['sp_attack'] = col
        elif cl in ['sp_defense', 'sp__def', 'sp_def', 'special_defense', 'spdef', 'sp__defense']:
            col_map['sp_defense'] = col
        elif cl in ['speed', 'spd']:
            col_map['speed'] = col
        elif cl in ['total', 'base_total', 'bst', 'total_stats']:
            col_map['total'] = col
        elif cl in ['is_legendary', 'legendary', 'islegendary']:
            col_map['legendary'] = col
    
    print(f"Identified columns: {col_map}\n")
    
    # calculate base stat total if not present
    stat_cols = ['hp', 'attack', 'defense', 'sp_attack', 'sp_defense', 'speed']
    available_stats = [col_map[s] for s in stat_cols if s in col_map]
    
    if 'total' not in col_map and len(available_stats) == 6:
        df['base_stat_total'] = df[available_stats].sum(axis=1)
        col_map['total'] = 'base_stat_total'
        print("Calculated base_stat_total from individual stats")
    
    # add stat tier classification
    if 'total' in col_map:
        total_col = col_map['total']
        df['stat_tier'] = pd.cut(
            pd.to_numeric(df[total_col], errors='coerce'),
            bins=[0, 300, 400, 500, 580, 700, 9999],
            labels=['Very Weak (<300)', 'Weak (300-399)', 'Average (400-499)', 
                    'Strong (500-579)', 'Very Strong (580-699)', 'Legendary (700+)']
        )
        print("Added stat_tier classification")
    
    # add type combination column
    if 'type1' in col_map:
        t1 = col_map['type1']
        if 'type2' in col_map:
            t2 = col_map['type2']
            df['type_combo'] = df.apply(
                lambda r: f"{r[t1]}" if pd.isna(r[t2]) or r[t2] == '' or str(r[t2]).lower() == 'nan'
                else f"{r[t1]} / {r[t2]}", axis=1
            )
            df['is_dual_type'] = df[t2].notna() & (df[t2] != '') & (df[t2].astype(str).str.lower() != 'nan')
        else:
            df['type_combo'] = df[t1]
            df['is_dual_type'] = False
        print("Added type_combo and is_dual_type columns")
    
    # add offensive/defensive/speed ratings
    if all(s in col_map for s in ['attack', 'sp_attack']):
        atk = pd.to_numeric(df[col_map['attack']], errors='coerce')
        spatk = pd.to_numeric(df[col_map['sp_attack']], errors='coerce')
        df['offensive_power'] = (atk + spatk).rank(pct=True).round(3) * 100
        print("Added offensive_power percentile")
    
    if all(s in col_map for s in ['defense', 'sp_defense', 'hp']):
        defn = pd.to_numeric(df[col_map['defense']], errors='coerce')
        spdef = pd.to_numeric(df[col_map['sp_defense']], errors='coerce')
        hp = pd.to_numeric(df[col_map['hp']], errors='coerce')
        df['defensive_bulk'] = (defn + spdef + hp).rank(pct=True).round(3) * 100
        print("Added defensive_bulk percentile")
    
    if 'speed' in col_map:
        spd = pd.to_numeric(df[col_map['speed']], errors='coerce')
        df['speed_tier'] = pd.cut(
            spd, bins=[0, 45, 70, 100, 130, 999],
            labels=['Very Slow', 'Slow', 'Average', 'Fast', 'Very Fast']
        )
        print("Added speed_tier classification")
    
    # add generation label
    if 'generation' in col_map:
        gen_col = col_map['generation']
        gen_labels = {1: 'Gen I (Kanto)', 2: 'Gen II (Johto)', 3: 'Gen III (Hoenn)',
                      4: 'Gen IV (Sinnoh)', 5: 'Gen V (Unova)', 6: 'Gen VI (Kalos)',
                      7: 'Gen VII (Alola)', 8: 'Gen VIII (Galar)', 9: 'Gen IX (Paldea)'}
        df['generation_label'] = pd.to_numeric(df[gen_col], errors='coerce').map(gen_labels)
        print("Added generation_label")
    
    # clean up
    df = df.replace(['', 'nan', 'None'], np.nan)
    
    # Save
    output_path = os.path.join(DATA_DIR, 'pokemon_powerbi_ready.csv')
    df.to_csv(output_path, index=False)
    print(f"\n=== OUTPUT ===")
    print(f"Saved: {output_path}")
    print(f"Shape: {df.shape[0]} rows, {df.shape[1]} columns")
    print(f"Columns: {df.columns.tolist()}")
    
    # quick stats
    if 'generation' in col_map:
        print(f"\nPokémon by generation:")
        print(df[col_map['generation']].value_counts().sort_index())
    
    if 'type1' in col_map:
        print(f"\nTop 10 primary types:")
        print(df[col_map['type1']].value_counts().head(10))
    
    return df


if __name__ == '__main__':
    print("=" * 60)
    print("POKEMON DATA PREPARATION FOR POWER BI")
    print("=" * 60)
    
    csv_files = load_and_explore()
    
    if not csv_files:
        print("No CSV files found in data/ directory!")
        print(f"Please place Pokémon datasets in: {DATA_DIR}")
    else:
        df = prepare_pokemon_data(csv_files)
        print("\nData preparation complete! Open 'pokemon_powerbi_ready.csv' in Power BI.")