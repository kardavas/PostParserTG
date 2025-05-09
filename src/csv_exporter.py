def export_to_csv(posts, filename):
    import csv

    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Post Content', 'Type', 'View Count'])  # Header row

        for post in posts:
            writer.writerow([post['content'], post['type'], post['views']])  # Data rows